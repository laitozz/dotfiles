local M = {}

M.get_hostname = function ()
  local handle = io.popen("hostname")
  if not handle then return nil end
  local result = handle:read("*l")
  handle:close()
  return result
end

return M
