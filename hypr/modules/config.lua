----------------
---- CONFIG ----
----------------

-- See https://wiki.hypr.land/Configuring/Basics/Variables/
hl.config({
    dwindle = {
        preserve_split = true, -- You probably want this
        force_split = 2,
    },
    -- See https://wiki.hyprland.org/Configuring/Master-Layout/ for more
    master = {
        new_status = "slave",
        new_on_top = true,
        mfact = 0.70,
    },
    -- See https://wiki.hyprland.org/Configuring/Scrolling-Layout/ for more
    scrolling = {
        fullscreen_on_one_column = true,
        column_width = 0.975,
        focus_fit_method = 0, -- center
    },
    cursor = {
        no_warps = true,
        hide_on_key_press = true,
    },
    xwayland = {
        force_zero_scaling = true,
    },
    misc = {
        focus_on_activate = true,
        enable_swallow = true,
        swallow_regex = "(scratch_term)|(Alacritty)|(kitty)",
    },
    --############
    --## INPUT ###
    --############
    -- https://wiki.hyprland.org/Configuring/Variables/#input
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
    -- Example per-device config
	-- See https://wiki.hypr.land/Configuring/Advanced-and-Cool/Devices/ for more
})
