# Contributing to AusTIMES VEDA Table CLI

Thank you for contributing to the AusTIMES VEDA Table CLI project!

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd times-tables
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install the package in editable mode with dev dependencies**:
   ```bash
   make install
   # or manually:
   pip install -e ".[dev]"
   ```

4. **Install bd (beads) for issue tracking** (optional but recommended):
   ```bash
   pip install beads
   ```

## Code Style and Quality

This project uses **ruff** for linting and formatting, and **pytest** for testing.

### Configuration

- **Line length**: 100 characters
- **Target Python**: 3.10+
- **Indentation**: 4 spaces (Python), 2 spaces (YAML/JSON)
- **Line endings**: LF (`\n`) on all platforms
- **Encoding**: UTF-8

### Before Committing

Run these checks before committing:

```bash
# Check code style
make lint

# Auto-fix style issues
make format

# Run tests
make test
```

### Code Standards

- **Type hints**: Required for all public functions
- **Docstrings**: Required for public APIs (modules, classes, functions)
- **Models**: Use dataclasses for all data models
- **Dependencies**: Prefer stdlib, avoid heavy dependencies
- **Logging**: 
  - `INFO` for CLI progress and user-facing messages
  - `DEBUG` for per-table details and internals
- **Error handling**: Clear, actionable error messages with context

## Testing Guidelines

### Test Organization

- **Unit tests**: `tests/unit/` - Test individual modules independently
- **Integration tests**: `tests/integration/` - Test end-to-end workflows
- **Fixtures**: `tests/fixtures/` - Sample test decks (keep small: <10 tables, <1000 rows)

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
pytest tests/ -v --cov=times_tables --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_extractor.py -v

# Run specific test
pytest tests/unit/test_extractor.py::test_extract_tables -v
```

### Writing Tests

- **Golden tests**: Verify deterministic CSV output (byte-for-byte identical)
- **Integration tests**: End-to-end extract → format → validate → diff → report
- **Keep fixtures small**: Test decks should be minimal but representative

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs or task lists.

### Quick Commands

```bash
# Check for ready work
bd ready --json

# Create new issue
bd create "Issue title" -t bug|feature|task -p 0-4 --json

# Claim issue
bd update bd-42 --status in_progress --json

# Complete issue
bd close bd-42 --reason "Completed" --json
```

### Workflow

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   ```bash
   bd create "Found bug" -p 1 --deps discovered-from:<parent-id>
   ```
5. **Complete**: `bd close <id> --reason "Done"`
6. **Commit together**: Always commit `.beads/issues.jsonl` with code changes

See [AGENTS.md](AGENTS.md) for full bd workflow details.

## Definition of Done

For an issue to be considered complete:

- ✅ Unit tests passing
- ✅ Golden determinism tests updated (if applicable)
- ✅ README updated for CLI or schema changes
- ✅ xl2times gaps documented via bd issues with `discovered-from` links
- ✅ `.beads/issues.jsonl` committed alongside code changes
- ✅ Code style checks pass (`make lint`)

## Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow code style guidelines
   - Write tests for new functionality
   - Update documentation as needed

3. **Run checks**:
   ```bash
   make lint
   make test
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```
   - Commit `.beads/issues.jsonl` with code changes if using bd

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **PR description should include**:
   - What problem does this solve?
   - How was it tested?
   - Any breaking changes?
   - Related bd issue IDs

## Determinism Invariants

To ensure stable Git diffs across platforms:

- **CSV encoding**: UTF-8
- **Newlines**: LF (`\n`) on all platforms
- **Quoting**: `csv.QUOTE_MINIMAL` (only when necessary)
- **Line terminator**: Explicit `lineterminator='\n'`
- **Header**: Canonical column order (from schema or first-seen)
- **Row order**: Lexicographic sort by primary key tuple
- **NULL representation**: Empty string in CSV, `None` internally

## Repository Structure

```
times-tables/
├── src/times_tables/    # Main package code
├── tests/                  # Test suite
│   ├── fixtures/          # Sample test decks (committed)
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docs/                   # Documentation
├── history/                # AI planning docs (ephemeral)
├── .beads/                 # bd issue tracking database
└── shadow/                 # Generated output (NOT committed)
```

## Getting Help

- **Documentation**: See [README.md](README.md) for project overview
- **Setup guide**: See [AGENTS.md](AGENTS.md) for development workflow
- **Issues**: Use `bd` to browse and track issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
