#!/bin/bash

export DISPLAY=:0

last_line=""
mouseMode="0"
cec-client | while read -r line; do
    # Ignorar líneas con ", 0)"
    if echo "$line" | grep -q ", 0)"; then
        continue
    fi

    # Ignorar líneas repetidas
    if [[ "$line" == "$last_line" ]]; then
        continue
    fi
    last_line="$line"
    if echo "$line" | grep -q "key pressed"; then
        # mouseMode enabled
        if echo "$line" | grep -q "up" && [[ "$mouseMode" == "1" ]]; then
            xdotool mousemove_relative -- 0 -30
        elif echo "$line" | grep -q "down" && [[ "$mouseMode" == "1" ]]; then
            xdotool mousemove_relative -- 0 30
        elif echo "$line" | grep -q "left" && [[ "$mouseMode" == "1" ]]; then
            xdotool mousemove_relative -- -30 0
        elif echo "$line" | grep -q "right" && [[ "$mouseMode" == "1" ]]; then
            xdotool mousemove_relative -- 30 0
        elif echo "$line" | grep -q "select" && [ "$mouseMode" == "1" ]; then
            xdotool click 1
        elif echo "$line" | grep -q "exit" && [ "$mouseMode" == "1" ]; then
            xdotool click 3
            # mouseMode disabled
        elif echo "$line" | grep -q "up" && [ "$mouseMode" == "0" ]; then
            xdotool key Up
        elif echo "$line" | grep -q "down" && [ "$mouseMode" == "0" ]; then
            xdotool key Down
        elif echo "$line" | grep -q "left" && [ "$mouseMode" == "0" ]; then
            xdotool key Left
        elif echo "$line" | grep -q "right" && [ "$mouseMode" == "0" ]; then
            xdotool key Right
        elif echo "$line" | grep -q "select" && [ "$mouseMode" == "0" ]; then
            xdotool key Return
        elif echo "$line" | grep -q "exit" && [ "$mouseMode" == "0" ]; then
            xdotool BackSpace
            # Resto de botones
        elif echo "$line" | grep -q "forward"; then
            xdotool key Tab
        elif echo "$line" | grep -q "backward"; then
            xdotool key shift+Tab
        elif echo "$line" | grep -q "F4 (yellow)"; then
            xdotool key F5
        elif echo "$line" | grep -q "F1 (blue)"; then
            xdotool key F11
        elif echo "$line" | grep -q "F2 (red)"; then
            xdotool key shift+S
        elif echo "$line" | grep -q "F3 (green)"; then
            xdotool key shift+M
        elif echo "$line" | grep -q "stop"; then
            if [[ "$mouseMode" == "1" ]]; then
                mouseMode="0"
            else
                mouseMode="1"
            fi
        fi
    fi
done
