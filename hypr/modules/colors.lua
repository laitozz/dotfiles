----------------
---- COLORS ----
----------------

G.colors = {}

local mg = require("hyprland-colors")

for name, color in pairs(require("hyprland-colors")) do
	G.colors[name] = color
end
