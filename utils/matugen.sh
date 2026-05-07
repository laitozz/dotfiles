#!/usr/bin/env bash

wd=~/dotfiles/imgs

file=/tmp/wpFile
# TODO: use something other than yazi
kitty yazi $wd --chooser-file $file
img=$(cat $file)
echo "$img"

# TODO: use matugen instead
# https://github.com/InioX/matugen/wiki
matugen image "$img" --source-color-index 1

# kitty @ action load_config_file
