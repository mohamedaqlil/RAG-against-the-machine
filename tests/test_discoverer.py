from pathlib import Path
import pytest

# Import your function from src
from src.chunking import file_discovery


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Fixture that creates a temporary directory tree simulating various file edge cases."""
    # 1. Valid files
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# Documentation")

    # 2. Nested valid files
    sub_dir = tmp_path / "src" / "nested"
    sub_dir.mkdir(parents=True)
    (sub_dir / "utils.py").write_text("def add(a, b): return a + b")
    (sub_dir / "guide.md").write_text("## Guide")

    # 3. Invalid extensions
    (tmp_path / "data.json").write_text("{}")
    (tmp_path / "script.sh").write_text("#!/bin/bash")

    # 4. Ignored directories and contents
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-310.pyc").write_text("compiled")
    (pycache / "trap.py").write_text("# Should be ignored")

    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    (git_dir / "pre-commit.py").write_text("# Should be ignored")

    venv_dir = tmp_path / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "site_package.py").write_text("# Should be ignored")

    # 5. Empty subdirectories (no files inside)
    (tmp_path / "empty_dir").mkdir()

    return tmp_path


# --- INDIVIDUAL CONDITION TESTS ---


def test_discovers_valid_extensions(temp_workspace: Path):
    """Verifies Condition: Collects .py and .md files."""
    files = file_discovery(temp_workspace)
    filenames = {f.name for f in files}

    assert "main.py" in filenames
    assert "README.md" in filenames
    assert "utils.py" in filenames
    assert "guide.md" in filenames


def test_ignores_non_target_extensions(temp_workspace: Path):
    """Verifies Condition: Rejects files that are not .py or .md."""
    files = file_discovery(temp_workspace)
    filenames = {f.name for f in files}

    assert "data.json" not in filenames
    assert "script.sh" not in filenames


def test_skips_directories(temp_workspace: Path):
    """Verifies Condition: skips items where not path.is_file()."""
    files = file_discovery(temp_workspace)

    for f in files:
        assert f.is_file(), f"Path {f} is a directory, not a file!"


def test_skips_ignored_directories(temp_workspace: Path):
    """Verifies Condition: skips paths containing any part in IGNORED_DIRS."""
    files = file_discovery(temp_workspace)
    filenames = {f.name for f in files}

    assert "trap.py" not in filenames
    assert "pre-commit.py" not in filenames
    assert "site_package.py" not in filenames


def test_empty_directory_returns_empty_list(tmp_path: Path):
    """Verifies Condition: Handles empty raw_dir gracefully without crashing."""
    empty_dir = tmp_path / "empty_raw"
    empty_dir.mkdir()

    files = file_discovery(empty_dir)
    assert files == []


def test_returns_path_objects(temp_workspace: Path):
    """Verifies Condition: Output list contains pathlib.Path objects."""
    files = file_discovery(temp_workspace)

    assert len(files) > 0
    for f in files:
        assert isinstance(f, Path)
