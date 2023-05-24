from itertools import chain
from typing import Optional

from pynvim_pp.nvim import Nvim
from std2 import anext

from ..registry import rpc
from ..settings.localization import LANG
from ..settings.types import Settings
from ..state.next import forward
from ..state.types import State
from ..view.ops import display_path
from .focus import _jump
from .shared.index import indices
from .types import Stage


def _display_path(state: State, idx: int) -> str:
    display = (
        display_path(path, state=state) if (path := state.bookmarks.get(idx)) else ""
    )
    return f"{idx}. {display}"


@rpc(blocking=False)
async def _bookmark_set(
    state: State, settings: Settings, is_visual: bool
) -> Optional[Stage]:
    """
    Set bookmark
    """

    if node := await anext(indices(state, is_visual=is_visual), None):
        opts = {
            k: v
            for k, v in chain(
                ((_display_path(state, idx=i), i) for i in range(1, 10)),
                ((LANG("clear_bookmarks", idx=0), 0),),
            )
        }
        if (mark := await Nvim.input_list(opts)) is not None:
            bookmarks = {**state.bookmarks, mark: node.path} if mark else {}
            new_state = await forward(state, settings=settings, bookmarks=bookmarks)
            return Stage(new_state)
        else:
            return None
    else:
        return None


@rpc(blocking=False)
async def _bookmark_goto(
    state: State, settings: Settings, is_visual: bool
) -> Optional[Stage]:
    """
    Goto bookmark
    """

    if marks := sorted(state.bookmarks.items()):
        opts = {_display_path(state, idx=i): p for i, p in marks}
        if mark := await Nvim.input_list(opts):
            return await _jump(state, settings=settings, path=mark)
        else:
            return None
    else:
        await Nvim.write(LANG("no_bookmarks"), error=True)
        return None