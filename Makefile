.PHONY: test lint format clean install help

help:
	@echo "Available targets:"
	@echo "  test     - Run pytest test suite"
	@echo "  lint     - Check code style with ruff"
	@echo "  format   - Auto-fix code style issues with ruff"
	@echo "  clean    - Remove build artifacts and cache files"
	@echo "  install  - Install package in editable mode with dev dependencies"

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check src/ tests/

format:
	python -m ruff check --fix src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf dist/ build/ *.egg-info

install:
	pip install -e ".[dev]"
