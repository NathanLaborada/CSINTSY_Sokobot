#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: $0 <map name> [--gui]"
    exit 1
fi
MODE="raw"
if [ "$2" = "--gui" ]; then
    MODE="bot"
fi
python -m src.main.driver "$1" $MODE