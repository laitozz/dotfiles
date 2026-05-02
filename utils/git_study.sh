#!/usr/bin/env bash

# A simple script to clone a repo to and look at its source files
# TODO: flag for cloning to /tmp instead
# TODO: help flag
# TODO: set up a special find for finding files in the ~/reference directory

repo="$1"
dir="${2:-$repo}"
tmux_session_name="reference"
tmux_session_dir="$HOME/reference/aauto/$dir"

git clone "https://github.com/$repo.git" "$tmux_session_dir"
cd "$tmux_session_dir" || exit 0
nvim 

# TODO: tmux session management
# if not tmux has-session -t=$name 2> /dev/null; then
#     tmux new-session -ds $name -c $dir
# fi
# tmux switch-client -t $name

