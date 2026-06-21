#!/usr/bin/env bash

if [[ "$QUTE_URL" == *"localhost"* ]]; then
	echo "fake-key j" >> "$QUTE_FIFO"
else
	echo "scroll down" >> "$QUTE_FIFO"
fi
