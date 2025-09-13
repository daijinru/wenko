#!/bin/bash

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

if [ -z "$VIRTUAL_ENV" ]; then
    source venv/bin/activate
fi

uv sync

uv run main.py
