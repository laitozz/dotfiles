hl.window_rule({
    name = "steam-special-workspace",
    match = {
        class = "steam",
    },
    workspace = "special:steam silent",
	float = false,
	maximize = true,
})

hl.window_rule({
    name = "games-out-of-steam-workspace",
    match = {
        workspace = "special:steam",
        class = "negative:steam",
    },
    workspace = "name:games",
})

-- Should fix the update popup doing weird stuff
hl.window_rule({
	match = { title = "^([Ss]team.*|[Gg]amescope|Extracting package.*|Verifying installation.*)$" },
	workspace = "special:steam silent"
})

hl.window_rule({
    match = {
        class = ".*",
    },
    suppress_event = "maximize activate activateFocus",
})

