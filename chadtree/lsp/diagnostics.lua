(function(_)
  local validate = (function()
    if not vim.api.nvim_call_function("has", {"nvim-0.11"}) then
      return vim.validate
    else
      return function(spec)
        for name, args in pairs(spec) do
          vim.validate(name, unpack(args))
        end
      end
    end
  end)()

  if vim.diagnostic then
    local diagnostics = vim.diagnostic.get(nil, nil)
    validate({diagnostics = {diagnostics, "table"}})
    local acc = {}
    for _, row in pairs(diagnostics) do
      local buf = row.bufnr
      local severity = tostring(row.severity)
      validate(
        {
          buf = {buf, "number"},
          row_severity = {row.severity, "number"}
        }
      )
      if not acc[buf] then
        acc[buf] = {}
      end
      if not acc[buf][severity] then
        acc[buf][severity] = 0
      end
      acc[buf][severity] = acc[buf][severity] + 1
    end
    local acc2 = {}
    for buf, warnings in pairs(acc) do
      local path = vim.api.nvim_buf_get_name(buf)
      acc2[path] = warnings
    end
    return acc2
  end
end)(...)
