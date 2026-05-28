-------------------
---- AUTOSTART ----
-------------------

-- See https://wiki.hypr.land/Configuring/Basics/Autostart/
hl.on("hyprland.start", function()
    hl.exec_cmd("wal -R -s &")
    hl.exec_cmd("awww-daemon &")
    hl.exec_cmd("noctalia-shell")
    hl.exec_cmd("emacs --daemon")
    hl.exec_cmd("hyprsunset")
    hl.exec_cmd("wl-paste --type text  --watch cliphist store")
    hl.exec_cmd("wl-paste --type image --watch cliphist store")
    hl.exec_cmd(terminal, { workspace = "1 silent" })
    hl.exec_cmd(browser, { workspace = "2 silent" })
    hl.exec_cmd(emacs .. " -a 'emacs'", { workspace = "9 silent" })
    hl.exec_cmd("qutebrowser", { workspace = "10 silent" })
end)

