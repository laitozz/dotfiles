-------------------
---- KEYBINDS  ----
-------------------

-- Base
hl.bind(G.mainMod .. " + Q", hl.dsp.exec_cmd(G.term))
hl.bind(G.mainMod .. " + C", hl.dsp.window.close())
hl.bind(G.mainMod .. " + M", hl.dsp.exec_cmd("wlogout"))
hl.bind(G.mainMod .. " + V", hl.dsp.exec_cmd("cliphist list | rofi -dmenu | cliphist decode | wl-copy"))
hl.bind(G.mainMod .. " + SHIFT + M", hl.dsp.exit())
hl.bind(G.mainMod .. " + F", hl.dsp.window.fullscreen({ mode = "fullscreen" }))

-- Applications
hl.bind(G.mainMod .. " + Space", hl.dsp.exec_cmd(G.menu))
hl.bind(G.mainMod .. " + SHIFT + W", hl.dsp.exec_cmd("wofi --show drun"))
hl.bind(G.mainMod .. " + SHIFT + T", hl.dsp.exec_cmd("tofi-run"))
hl.bind(G.mainMod .. " + SHIFT + O", hl.dsp.exec_cmd(G.terminal))
hl.bind(G.mainMod .. " + SHIFT + F", hl.dsp.exec_cmd("firefox"))
hl.bind(G.mainMod .. " + SHIFT + B", hl.dsp.exec_cmd("qutebrowser"))
hl.bind(G.mainMod .. " + SHIFT + E", hl.dsp.exec_cmd(G.emacs))
hl.bind(G.mainMod .. " + SHIFT + S", hl.dsp.exec_cmd("grim -g \"$(slurp)\" - | wl-copy"))
hl.bind(G.mainMod .. " + Return", hl.dsp.exec_cmd("kitty"))

-- Internal
hl.bind(G.mainMod .. " + F1", hl.dsp.exec_cmd("firefox https://wiki.hypr.land/Configuring/Window-Rules"))
hl.bind(G.mainMod .. " + F2", hl.dsp.exec_cmd("kitty nvim ~/.config/hypr/hyprland.conf"))
hl.bind(G.mainMod .. " + F5", hl.dsp.exec_cmd("~/dotfiles/utils/matugen.sh"))
hl.bind(G.mainMod .. " + F7", hl.dsp.exec_cmd("noctalia-shell kill; noctalia-shell &"))
hl.bind(G.mainMod .. " + F8", hl.dsp.exec_cmd("~/.config/hypr/gamemode.sh"))

-- Keyboard switching
hl.bind("CTRL + SHIFT + 8", hl.dsp.exec_cmd("hyprctl switchxkblayout keyd-virtual-keyboard 1"))
hl.bind("CTRL + SHIFT + 9", hl.dsp.exec_cmd("hyprctl switchxkblayout keyd-virtual-keyboard 0"))

-- Tiling
hl.bind(G.mainMod .. " + T", hl.dsp.submap("tiling"))
hl.define_submap("tiling", function()
	hl.bind(G.mainMod .. " + V", hl.dsp.window.float({ action = "toggle" }))
	hl.bind(G.mainMod .. " + P", hl.dsp.window.pseudo())
	hl.bind(G.mainMod .. " + T", hl.dsp.layout("togglesplit"))
	hl.bind(G.mainMod .. " + F", hl.dsp.layout("swapwithmaster"))
	hl.bind("catchall", hl.dsp.submap("reset"))
end)

-- Navigation
hl.bind(G.mainMod .. " + l", hl.dsp.focus({ direction = "right" }))
hl.bind(G.mainMod .. " + h", hl.dsp.focus({ direction = "left" }))
hl.bind(G.mainMod .. " + k", hl.dsp.focus({ direction = "up" }))
hl.bind(G.mainMod .. " + j", hl.dsp.focus({ direction = "down" }))
hl.bind(G.mainMod .. " + SHIFT + l", hl.dsp.window.move({ direction = "r" }))
hl.bind(G.mainMod .. " + SHIFT + h", hl.dsp.window.move({ direction = "l" }))
hl.bind(G.mainMod .. " + SHIFT + k", hl.dsp.window.move({ direction = "u" }))
hl.bind(G.mainMod .. " + SHIFT + j", hl.dsp.window.move({ direction = "d" }))
hl.bind("SUPER + CTRL + h", hl.dsp.layout("preselect l"))
hl.bind("SUPER + CTRL + j", hl.dsp.layout("preselect d"))
hl.bind("SUPER + CTRL + k", hl.dsp.layout("preselect u"))
hl.bind("SUPER + CTRL + l", hl.dsp.layout("preselect r"))
hl.bind("SUPER + CTRL + Space", hl.dsp.layout("preselect cancel"))

-- Workspaces
for i = 1, 10 do
    local key = i % 10 -- 10 maps to key 0
    hl.bind(G.mainMod .. " + " .. key,             hl.dsp.focus({ workspace = i}))
    hl.bind(G.mainMod .. " + SHIFT + " .. key,     hl.dsp.window.move({ workspace = i }))
end
hl.bind(G.mainMod .. " + grave", hl.dsp.focus({ workspace = "name:games" }))

-- Mouse
hl.bind(G.mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(G.mainMod .. " + mouse_up", hl.dsp.focus({ workspace = "e-1" }))
hl.bind(G.mainMod .. " + mouse:272", hl.dsp.window.drag())
hl.bind(G.mainMod .. " + mouse:273", hl.dsp.window.resize())

-- Function keys
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked = true, repeating = true })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true, repeating = true })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl s 10%+"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl s 10%-"), { locked = true, repeating = true })
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })
