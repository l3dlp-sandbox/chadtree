from contextlib import suppress
from json import dumps
from mimetypes import guess_type
from os.path import getsize, normpath, relpath
from pathlib import Path, PurePath
from posixpath import sep
from typing import AsyncContextManager, Optional, cast

from pynvim_pp.buffer import Buffer
from pynvim_pp.hold import hold_win
from pynvim_pp.nvim import Nvim
from pynvim_pp.window import Window
from std2 import anext
from std2.aitertools import achain, to_async
from std2.contextlib import nullacontext

from ...settings.localization import LANG
from ...state.next import forward
from ...state.types import State
from ..types import ClickType, Stage
from .wm import (
    find_buffers_with_file,
    find_non_fm_windows_in_tab,
    find_window_with_file_in_tab,
    new_window,
    resize_fm_windows,
)

_KB = 1000


async def _show_file(*, state: State, click_type: ClickType) -> None:
    if click_type is ClickType.tertiary:
        await Nvim.exec("tabnew")
        win = await Window.get_current()
        for key, val in state.settings.win_actual_opts.items():
            await win.opts.set(key, val=val)

    if path := state.current:
        mgr = (
            cast(AsyncContextManager[None], hold_win(win=None))
            if click_type is ClickType.secondary
            else nullacontext(None)
        )
        async with mgr:
            non_fm_windows = [
                win
                async for win in find_non_fm_windows_in_tab(
                    last_used=state.window_order
                )
            ]
            buf = await anext(find_buffers_with_file(file=path), None)
            win = await anext(
                achain(
                    find_window_with_file_in_tab(
                        last_used=state.window_order, file=path
                    ),
                    to_async(non_fm_windows),
                ),
                cast(Window, None),
            ) or await new_window(
                last_used=state.window_order,
                win_local=state.settings.win_actual_opts,
                open_left=not state.settings.open_left,
                width=(
                    None
                    if len(non_fm_windows)
                    else await Nvim.opts.get(int, "columns") - state.width - 1
                ),
            )

            await Window.set_current(win)
            non_fm_count = len(non_fm_windows)

            if click_type is ClickType.v_split and non_fm_count:
                await Nvim.exec("vnew")
                temp_buf = await Buffer.get_current()
                await temp_buf.opts.set("bufhidden", val="wipe")
            elif click_type is ClickType.h_split and non_fm_count:
                await Nvim.exec("new")
                temp_buf = await Buffer.get_current()
                await temp_buf.opts.set("bufhidden", val="wipe")

            win = await Window.get_current()

            if buf:
                await win.set_buf(buf)
            else:
                cwd = await Nvim.getcwd()
                escaped = await Nvim.fn.fnameescape(str, relpath(normpath(path), cwd))
                await Nvim.exec(f"edit! {escaped}")

            await resize_fm_windows(last_used=state.window_order, width=state.width)


async def open_file(
    state: State, path: PurePath, click_type: ClickType
) -> Optional[Stage]:
    mime, _ = guess_type(path.name, strict=False)
    m_type, _, _ = (mime or "").partition(sep)

    text, size = True, 0
    with suppress(OSError):
        with Path(path).open() as fd:
            try:
                fd.readline(_KB)
            except UnicodeDecodeError:
                text = False

        # size = getsize(fd.fileno())

    question = LANG(
        "mime_warn", name=dumps(path.name, ensure_ascii=False), mime=str(mime)
    )

    go = (
        await Nvim.confirm(
            question=question,
            answers=LANG("ask_yesno"),
            answer_key={1: True, 2: False},
        )
        if (
            m_type in state.settings.mime.warn
            and path.suffix not in state.settings.mime.allow_exts
        )
        or not text
        else True
    )

    if go:
        new_state = await forward(state, current=path)
        await _show_file(state=new_state, click_type=click_type)
        return Stage(new_state, focus=path)
    else:
        return None
