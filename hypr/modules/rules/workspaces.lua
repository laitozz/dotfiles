hl.workspace_rule({
    workspace = "1",
	default = true,
})

hl.workspace_rule({
    workspace = "10",
    layout = "scrolling",
})

-- So that we can have rounding on scratchpads
for i = 1, 10 do
	hl.workspace_rule({
		workspace = "" .. i,
		no_rounding = true,
		no_shadow = true,
	})
end
