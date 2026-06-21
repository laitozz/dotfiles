#!/usr/bin/env bash

if [[ "$QUTE_URL" == *"localhost"* ]] || [[ "$QUTE_URL" == *"duckduckgo"* ]] || [[ "$QUTE_URL" == *"brave"* ]]; then
  echo "fake-key <Control-Return>" >> "$QUTE_FIFO"
else
	echo "fake-key <Return>" >> "$QUTE_FIFO"
fi
