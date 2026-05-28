---------------------
---- SCRATCHPADS ----
---------------------

local scratchpadSize = "size (monitor_w*0.8) (monitor_h*0.8)"

-- scratchpad definitions
local scratchpads  = {
	["terminal"]   = { key = "Y", exec = "kitty" },
	["nh"]         = { key = "U", exec = "kitty ~/dotfiles/utils/nh.sh" },
	["spotify"]    = { key = "P", exec = "kitty ncspot" },
	["impala"]     = { key = "I", exec = "kitty impala" },
	["steam"]      = { key = "G", exec = "steam" },
	["kdeconnect"] = { key = "K", exec = "kdeconnect-app" },
	["bluetui"]    = { key = "B", exec = "kitty bluetui" },
	["btop"]       = { key = "O", exec = "kitty btop" },
	["hyprland"]   = { key = "H", exec = "kitty nvim ~/dotfiles/hypr/" },
}

-- Initialize scratchpads
for name, pad in pairs(scratchpads) do
	hl.workspace_rule({
		workspace = "special:" .. name,
		["on_created_empty"] = "[float; " .. scratchpadSize .. "]" .. pad.exec,
		persistent = false,
	})
end


-- Binds for scratchpads
hl.bind(G.mainMod .. " + S", hl.dsp.submap("scratchpads"))
hl.define_submap("scratchpads", function()
	for name, pad in pairs(scratchpads) do
		hl.bind(G.mainMod .. " + " .. pad.key, hl.dsp.workspace.toggle_special(name))
	end
	hl.bind(G.mainMod .. " + S", hl.dsp.no_op())
	hl.bind("catchall", hl.dsp.submap("reset"))
end)
