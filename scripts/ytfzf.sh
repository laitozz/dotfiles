#!/usr/bin/env sh

query="$*"
[ -z "$query" ] && printf "Search: " && read -r query

yt-dlp "ytsearch20:$query" \
  --flat-playlist \
  --print "%(title)s	%(url)s" |
fzf --with-nth=1 --delimiter='\t' |
cut -f2- |
xargs -r mpv
