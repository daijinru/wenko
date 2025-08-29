@echo off

if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate.bat

:: 使用 uv sync 替代 pip install，排除 uvloop
uv sync --exclude uvloop

uv run main.py