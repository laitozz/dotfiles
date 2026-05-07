#!/usr/bin/env bash

wd=~/dotfiles/imgs

file=/tmp/wpFile
# TODO: make window float
kitty yazi $wd --chooser-file $file
img=$(cat $file)

img=$(find ~/.dotfiles/imgs -type f | wofi -d)

# TODO: use matugen instead
# https://github.com/InioX/matugen/wiki
wal -qsi "$img"

cp "$img" ~/.cache/wallpaper

awww img "$img" --transition-step 5 -t wave

noctalia-shell kill; noctalia-shell &
kitty @ action load_config_file
