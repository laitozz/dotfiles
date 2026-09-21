-- Should fix the update popup doing weird stuff
hl.window_rule({
	match = { title = "^([Ss]team.*|[Gg]amescope|Extracting package.*|Verifying installation.*)$" },
	workspace = "name:games"
})

hl.window_rule({
    match = {
        class = ".*",
    },
    suppress_event = "maximize activate activateFocus",
})

