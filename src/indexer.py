import os, pathlib
from pathlib import Path

RAW_DIR = "data/raw"

raw_dir = Path(RAW_DIR)
IGNORED_DIRS = {"__pycache__", ".git", ".venv", ".mypy_cache"}

def file_discovery(raw_dir):
    paths = []
    for i, path in enumerate(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        # if any(part in IGNORED_DIRS for part in path.parts):
        #     continue
        if path.suffix in {".py", ".md"}:
            paths.append(path)
