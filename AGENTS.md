## Project Goal

**AusTIMES VEDA Table CLI** is a Git-friendly tool for extracting, validating, and diffing VEDA-TIMES energy model input tables from Excel workbooks. It creates canonical CSV "shadow tables" that enable structured version control, row-level diffs, and rich HTML reports.

**Key approach**:
- Extract VEDA tables via xl2times integration
- Maintain stable table identifiers across workbook/sheet moves
- Deterministic CSV formatting for reliable Git diffs
- Structured diffing with workbook/sheet/table organization
- Self-contained HTML reports for human review

**Current phase**: Phase 1 - Core CLI commands (extract, format, validate, diff, report)

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**
```bash
bd ready --json
```

**Create new issues:**
```bash
bd create "Issue title" -t bug|feature|task -p 0-4 --json
bd create "Issue title" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**
```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**
```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`
6. **Commit together**: Always commit the `.beads/issues.jsonl` file together with the code changes so issue state stays in sync with code state

### Auto-Sync

bd automatically syncs with git:
- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### MCP Server (Recommended)

If using Claude or MCP-compatible clients, install the beads MCP server:

```bash
pip install beads-mcp
```

Add to MCP config (e.g., `~/.config/claude/config.json`):
```json
{
  "beads": {
    "command": "beads-mcp",
    "args": []
  }
}
```

Then use `mcp__beads__*` functions instead of CLI commands.

### Managing AI-Generated Planning Documents

AI assistants often create planning and design documents during development:
- PLAN.md, IMPLEMENTATION.md, ARCHITECTURE.md
- DESIGN.md, CODEBASE_SUMMARY.md, INTEGRATION_PLAN.md
- TESTING_GUIDE.md, TECHNICAL_DESIGN.md, and similar files

**Best Practice: Use a dedicated directory for these ephemeral files**

**Recommended approach:**
- Create a `history/` directory in the project root
- Store ALL AI-generated planning/design docs in `history/`
- Keep the repository root clean and focused on permanent project files
- Only access `history/` when explicitly asked to review past planning

**Example .gitignore entry (optional):**
```
# AI planning documents (ephemeral)
history/
```

**Benefits:**
- ✅ Clean repository root
- ✅ Clear separation between ephemeral and permanent documentation
- ✅ Easy to exclude from version control if desired
- ✅ Preserves planning history for archeological research
- ✅ Reduces noise when browsing the project

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ✅ Store AI planning docs in `history/` directory
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems
- ❌ Do NOT clutter repo root with planning documents

For more details, see README.md and QUICKSTART.md.

## Repository Conventions

### Package Management

This project uses **uv** for Python package management. Do NOT use pip, poetry, or other tools.

- **Installing dependencies**: `uv sync --all-extras`
- **Adding new packages**: `uv add <package-name>`
- **Running commands**: `uv run <command>` or activate venv first
- **Development install**: `uv sync --all-extras` (includes dev dependencies)

### Code Output Location

- **shadow/** - Generated output, do NOT commit
- **tests/fixtures/** - Sample test decks (small, commit to repo)
- **history/** - AI-generated planning documents (optional .gitignore)

### Determinism Invariants

To ensure stable Git diffs across platforms:

- **CSV encoding**: UTF-8
- **Newlines**: LF (`\n`) on all platforms
- **Quoting**: `csv.QUOTE_MINIMAL` (only when necessary)
- **Line terminator**: Explicit `lineterminator='\n'`
- **Header**: Canonical column order (from schema or first-seen)
- **Row order**: Lexicographic sort by primary key tuple (strings, case-sensitive)
- **NULL representation**: Empty string in CSV, `None` internally

### Large File Safety

- HTML reports truncate detailed row output by default (default: 2000 rows across entire report)
- Use `--limit-rows N` to override
- Diff summaries are always complete (counts, table lists)

### Definition of Done (Phase 1)

For an issue to be considered complete:

- ✅ Unit tests passing
- ✅ Golden determinism tests updated (if applicable)
- ✅ README updated for CLI or schema changes
- ✅ xl2times gaps documented via bd issues with `discovered-from` links
- ✅ `.beads/issues.jsonl` committed alongside code changes

### Coding Standards

- **Models**: Use dataclasses for all data models
- **Dependencies**: Prefer stdlib, avoid heavy dependencies
- **Logging**: 
  - `INFO` for CLI progress and user-facing messages
  - `DEBUG` for per-table details and internals
- **Error handling**: Clear, actionable error messages with context
- **Type hints**: Required for all public functions

### Local Development Quickstart

```bash
# Install dependencies with uv
uv sync --all-extras

# Run tests
uv run pytest

# Check code style
uv run ruff check .

# Run on sample deck
uv run austimes-tables extract tests/fixtures/sample_deck
uv run austimes-tables validate tests/fixtures/sample_deck
```

### Testing Guidelines

- **Unit tests**: Cover each module independently
- **Golden tests**: Verify deterministic CSV output (byte-for-byte identical)
- **Integration tests**: End-to-end extract → format → validate → diff → report
- **Fixtures**: Keep test decks small (<10 tables, <1000 rows total)

### xl2times Integration Notes

The tool integrates with xl2times via a thin adapter layer (`xl2_adapter.py`). If xl2times doesn't expose required metadata:

- **Missing PK**: Log warning, proceed with first-seen order, fail validate if PK not determinable
- **Missing column order**: Use first-seen order, persist in `tables_index.json`
- **Missing schema**: Log warning, proceed with best-effort validation

Create bd issues for any xl2times gaps discovered during development with `discovered-from` links.
