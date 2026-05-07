#!/usr/bin/env bash

# A simple script to clone a repo to and look at its source files
# TODO: flag for cloning to /tmp instead
# TODO: help flag
# TODO: set up a special find for finding files in the ~/reference directory

repo="$1"
dir="${2:-$repo}"

tmux_session_name=$(basename "$repo" | tr . _)
tmux_session_dir="$HOME/reference/aauto/$dir"

# TODO: check if $repo already starts with https://

git clone "https://github.com/$repo.git" "$tmux_session_dir" --depth 1 --recursive
cd "$tmux_session_dir" || exit 0
nvim 

if ! tmux has-session -t="$tmux_session_name" 2> /dev/null; then
    tmux new-session -ds "$tmux_session_name" -c "$tmux_session_dir"
fi

tmux switch-client -t "$tmux_session_name"
