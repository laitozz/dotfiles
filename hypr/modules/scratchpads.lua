---------------------
---- SCRATCHPADS ----
---------------------

local scratchpadSize = "size (monitor_w*0.8) (monitor_h*0.8)"

-- TODO: dictionary and a loop

hl.workspace_rule({
    workspace = "special:terminal",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] kitty",
    persistent = false,
})

hl.workspace_rule({
    workspace = "special:nh",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] kitty ~/dotfiles/utils/nh.sh",
    persistent = false,
})

hl.workspace_rule({
    workspace = "special:spotify",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] kitty ncspot",
    persistent = false,
})

hl.workspace_rule({
    workspace = "special:impala",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] kitty impala",
    persistent = false,
})

hl.workspace_rule({
    workspace = "special:steam",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] steam",
    persistent = false,
})

hl.workspace_rule({
    workspace = "special:kdeconnect",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] kdeconnect-app",
    persistent = false,
})

hl.workspace_rule({
    workspace = "special:bluetui",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] kitty bluetui",
    persistent = false,
})

hl.workspace_rule({
    workspace = "special:btop",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] kitty btop",
    persistent = false,
})

hl.workspace_rule({
    workspace = "special:hyprland",
    ["on_created_empty"] = "[float; " .. scratchpadSize .. "] kitty nvim ~/dotfiles/hypr/hyprland.conf",
    persistent = false,
})

hl.bind(G.mainMod .. " + S", hl.dsp.submap("scratchpads"))
hl.define_submap("scratchpads", function()
	hl.bind(G.mainMod .. " + P", hl.dsp.workspace.toggle_special("spotify"))
	hl.bind(G.mainMod .. " + U", hl.dsp.workspace.toggle_special("nh"))
	hl.bind(G.mainMod .. " + Y", hl.dsp.workspace.toggle_special("terminal"))
	hl.bind(G.mainMod .. " + I", hl.dsp.workspace.toggle_special("impala"))
	hl.bind(G.mainMod .. " + G", hl.dsp.workspace.toggle_special("steam"))
	hl.bind(G.mainMod .. " + K", hl.dsp.workspace.toggle_special("kdeconnect"))
	hl.bind(G.mainMod .. " + B", hl.dsp.workspace.toggle_special("bluetui"))
	hl.bind(G.mainMod .. " + M", hl.dsp.workspace.toggle_special("btop"))
	hl.bind(G.mainMod .. " + H", hl.dsp.workspace.toggle_special("hyprland"))
	hl.bind(G.mainMod .. " + S", hl.dsp.no_op())
	hl.bind("catchall", hl.dsp.submap("reset"))
end)
