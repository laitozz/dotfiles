#!/usr/bin/env bash

# Focuses the most common insert element on each site

if [[ "$QUTE_URL" == *"duckduckgo.com"* ]]; then
	echo 'jseval document.getElementById("search_form_input").focus()' >> "$QUTE_FIFO"
fi

if [[ "$QUTE_URL" == *"claude.ai"* ]]; then
	echo "jseval document.querySelector('div[contenteditable=true]').focus()" >> "$QUTE_FIFO"
fi

echo 'mode-enter insert' >> "$QUTE_FIFO"
# echo 'fake-key <Ctrl-A>' >> "$QUTE_FIFO"
