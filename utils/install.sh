#!/usr/bin/env bash

set -euo pipefail

# include hidden files
shopt -s dotglob

DOTFILES_DIR="${1:-$HOME/dotfiles}"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

mkdir -p "$XDG_CONFIG_HOME"

for path in "$DOTFILES_DIR"/*; do
    name="$(basename "$path")"

    # Skip non-existent glob matches
    [[ -e "$path" ]] || continue

	# Skip git paths
	[[ "$name" =~ ^\.git.*$ ]] && continue

	# Skip internal
	[[ "$name" =~ ^(nixos)|(misc)|(utils)$ ]] && continue 

    if [[ -d "$path" ]]; then
        target="$XDG_CONFIG_HOME/$name"

    elif [[ -f "$path" ]]; then
        target="$HOME/$name"

    else
        echo "Skipping unsupported file type: $path"
        continue
    fi

    if [[ -L "$target" || -e "$target" ]]; then
        echo "Existing target: $target"
		continue
    fi

    echo "Linking $path -> $target"
    ln -s "$path" "$target"
done
