#!/usr/bin/env bash

if [[ "$QUTE_URL" == *"localhost"* ]]; then
  echo "fake-key k" >> "$QUTE_FIFO"
else
	echo "scroll up" >> "$QUTE_FIFO"
fi
