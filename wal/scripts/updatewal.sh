#!/usr/bin/env bash

wd=~/dotfiles/imgs


file=/tmp/wpFile
# TODO: make window float
kitty yazi $wd --chooser-file $file
img=$(cat $file)

# img=$(find ~/.dotfiles/imgs -type f | wofi -d)

echo "$img" >> /tmp/txt

wal -qsi "$img"

cp "$img" ~/.cache/wallpaper

awww img "$img" --transition-step 5 -t wave

# update the theme of every neovim instance
# for addr in "$XDG_RUNTIME_DIR"/nvim.*.0; do
#     nvim --server "$addr" --remote-send ':colorscheme pywal<CR>'
# done
 
pkill waybar; waybar &
kitty @ action load_config_file
