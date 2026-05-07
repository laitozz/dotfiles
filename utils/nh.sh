#!/usr/bin/env sh

# From https://github.com/fish-shell/fish-shell/discussions/11667

fish --init-command="function nhr --on-event fish_prompt
    commandline -i 'nh os switch'
end
"
