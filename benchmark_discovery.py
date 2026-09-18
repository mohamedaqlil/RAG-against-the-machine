import time
from pathlib import Path

RAW_DIR = Path("data/raw")
IGNORED_DIRS = {"__pycache__", ".git", ".venv", "node_modules", ".mypy_cache"}


# 1. Discovery WITHOUT the ignore condition
def discover_without_ignore(raw_dir: Path) -> list[Path]:
    paths = []
    for path in raw_dir.rglob("*"):
        if not path.is_file():
            continue
        # NO ignore filter check here
        if path.suffix in {".py", ".md"}:
            paths.append(path)
    return paths


# 2. Discovery WITH the ignore condition
def discover_with_ignore(raw_dir: Path) -> list[Path]:
    paths = []
    for path in raw_dir.rglob("*"):
        if not path.is_file():
            continue
        # WITH early path pruning
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix in {".py", ".md"}:
            paths.append(path)
    return paths


if __name__ == "__main__":
    print("--- RUNNING BENCHMARK ---")

    # Measure WITHOUT ignore
    start_time = time.perf_counter()
    files_without = discover_without_ignore(RAW_DIR)
    time_without = time.perf_counter() - start_time

    # Measure WITH ignore
    start_time = time.perf_counter()
    files_with = discover_with_ignore(RAW_DIR)
    time_with = time.perf_counter() - start_time

    # Output Results Matrix
    print(f"\n1. WITHOUT Ignore Condition:")
    print(f"   - Total Files Found: {len(files_without)}")
    print(f"   - Execution Time:   {time_without:.6f} seconds")

    print(f"\n2. WITH Ignore Condition:")
    print(f"   - Total Files Found: {len(files_with)}")
    print(f"   - Execution Time:   {time_with:.6f} seconds")

    print(f"\n3. Difference / Delta:")
    print(f"   - Extra Files Caught without filter: {len(files_without) - len(files_with)}")
    print(f"   - Time Difference:                  {abs(time_without - time_with):.6f} seconds")
