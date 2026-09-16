install:
	pip install uv
	uv sync

run:
	uv run python -m src <command>

debug:
	uv run python -pdb -m src <command>

clean:
	rm -rf  __pycache__
	rm -rf *.mypy_cache

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
