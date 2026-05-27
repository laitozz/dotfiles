#!/usr/bin/env bash

echo 'jseval document.getElementById("search_form_input").focus()' >> "$QUTE_FIFO"
echo 'mode-enter insert' >> "$QUTE_FIFO"
# echo 'fake-key <Ctrl-A>' >> "$QUTE_FIFO"
