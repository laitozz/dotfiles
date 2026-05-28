local M = {}

M.get_hostname = function ()
  local handle = io.popen("hostname")
  if not handle then return nil end
  local result = handle:read("*l")
  handle:close()
  return result
end

M.print = function (arg)
	hl.exec_cmd("hyprctl notify 2 3000 '#00F' " .. arg)
end

return M
