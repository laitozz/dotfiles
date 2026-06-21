#!/usr/bin/env bash

# Focuses the most common insert element on each site
# NOTE: can also use gi for most things

if [[ "$QUTE_URL" == *"duckduckgo.com"* ]]; then
	echo 'jseval -q document.getElementById("search_form_input").focus()' >> "$QUTE_FIFO"
elif [[ "$QUTE_URL" == *"claude.ai"* ]]; then
	echo "jseval -q document.querySelector('div[contenteditable=true]').focus()" >> "$QUTE_FIFO"
elif [[ "$QUTE_URL" == *"searx"* ]] || [[ "$QUTE_URL" == *"localhost"* ]]; then
	echo 'jseval -q document.getElementById("q").focus()' >> "$QUTE_FIFO"
fi

echo 'mode-enter insert' >> "$QUTE_FIFO"
echo 'fake-key <End>' >> "$QUTE_FIFO"
