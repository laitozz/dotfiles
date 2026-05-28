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

---------------
---- INPUT ----
---------------

-- See https://wiki.hypr.land/Configuring/Basics/Variables/#input
input = {
	kb_layout = "us,fi",
	kb_variant = "",
	kb_model = "",
	-- kb_options = ctrl:nocaps # Done on system level
	kb_rules = "",
	follow_mouse = 1,
	sensitivity = 0, -- -1.0 - 1.0, 0 means no modification.
	touchpad = {
		natural_scroll = false,
	},
},

hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
