------------------
---- Hardware ----
------------------

-- See https://wiki.hypr.land/Configuring/Basics/Monitors/

local scale = 1.0
if G.hostname == "fenix" then
	scale = 1.2
end

hl.monitor({
	output = "",
	mode = "1920x1080",
	position = "0x0",
	scale = scale,
})

-- See https://wiki.hypr.land/Configuring/Advanced-and-Cool/Devices/
hl.device({
    name = "epic-mouse-v1",
    sensitivity = -0.5,
})

hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
