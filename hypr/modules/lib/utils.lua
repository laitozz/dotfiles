local M = {}

M.get_hostname = function ()
  local handle = io.popen("hostname")
  if not handle then return nil end
  local result = handle:read("*l")
  handle:close()
  return result
end

--- Sent a hyprland notification
M.print = function (arg, duration)
	if not G.debug then return end
	duration = duration or 3000
	hl.notification.create({ text = arg, duration = duration, icon = 1, font_size = 18 })
end

--- Print a table
M.tprint = function (arg)
	text = "{ \n"
	for k,v in pairs(arg) do
		text = text .. "\t" .. k .. " = " .. v .. "\n"
	end
	text = text .. "}"
	M.print(text, 3 * string.len(text))
end

--- Change the alpha value of color
--- @param color string
M.update_alpha = function (color, alpha)
	local new = color:gsub("[%d%w][%d%w]%)$", alpha .. ")")
	G.lib.print(new)
	return new
end

return M
