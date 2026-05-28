----------------
---- CONFIG ----
----------------

hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 10,
        border_size = 1,
        -- https://wiki.hyprland.org/Configuring/Variables/#variable-types for info about colors
        -- col.active_border = rgba(33ccffee) rgba(00ff99ee) 45deg
        -- col.inactive_border = rgba(595959aa)
        col = {
            -- active_border = color1 .. " " .. color2 .. " 45deg",
        },
        -- col.inactive_border = $background $color0 45deg
        -- col.inactive_border = $background
        -- Set to true enable resizing windows by clicking and dragging on borders and gaps
        resize_on_border = false,
        -- Please see https://wiki.hyprland.org/Configuring/Tearing/ before you turn this on
        allow_tearing = false,
        layout = "dwindle",
        no_focus_fallback = true,
    },
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
        fullscreen_on_one_column = false,
        column_width = 0.95,
        focus_fit_method = 0,
    },
    cursor = {
        no_warps = true,
        hide_on_key_press = true,
    },
    xwayland = {
        force_zero_scaling = true,
    },
    -- https://wiki.hyprland.org/Configuring/Variables/#misc
    misc = {
        -- force_default_wallpaper = 0 # Set to 0 or 1 to disable the anime mascot wallpapers
        -- disable_hyprland_logo = true # If true disables the random hyprland logo / anime girl background. :(
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
