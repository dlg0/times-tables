# Publishing (Git/GitHub) — austimes-tables

Primary distribution is the public GitHub repo `dlg0/times-tables`. Users install with uv directly from a Git tag:

    uv tool install git+https://github.com/dlg0/times-tables@vX.Y.Z

Pin to a tag (recommended) for reproducibility.

## Prerequisites (one-time)
- Python 3.10+ and uv or pip
- Write access to https://github.com/dlg0/times-tables
- Optional: pre-commit installed and hooks set up

Set upstream (if needed):
```bash
git remote add origin git@github.com:dlg0/times-tables.git
git fetch origin
```

## Local quality gates

Commands:
- Tests:          pytest
- Lint:           ruff check .
- Format:         ruff format .
- Fix lint/format: run ruff format . then ruff check . --fix

Recommended local setup:
```bash
# Using uv (recommended)
uv sync --all-extras
# Or with pip
pip install -e ".[dev]"
```

## Versioning and tags

- SemVer:
  - PATCH (x.y.Z): bugfixes, no CLI or CSV semantics change
  - MINOR (x.Y.z): backward-compatible features
  - MAJOR (X.y.z): breaking CLI flags/behavior or output schema/format changes
- Tag format: annotated tags `vX.Y.Z` (e.g., v0.1.1)
- Users should install pinning tags (e.g., @v0.1.1)

Bumping version (choose one):

1) Simple/manual:
- Edit `pyproject.toml` `[project].version` to the new SemVer.
- Commit that change.

2) Via Hatch (no project changes needed):
```bash
uvx hatch version [patch|minor|major]
```

## Release workflow (branch → PR → merge → tag)

1) Ensure main is up to date:
```bash
git checkout main
git pull origin main
```

2) Create a release branch:
```bash
git checkout -b release/vX.Y.Z
```

3) Run tests:
```bash
pytest
```
Fix any failures, iterate until green.

4) Format and lint:
```bash
ruff format .
ruff check . --fix
```

5) Re-run tests if any code changed:
```bash
pytest
```

6) Commit quality fixes and version bump:
```bash
# If using manual bump, edit pyproject.toml version now
git add .
git commit -m "chore: prepare release vX.Y.Z (format/lint/tests/version)"
git push -u origin release/vX.Y.Z
```

7) Open a Pull Request to main. Wait for CI to pass. Address feedback if any.

8) Merge the PR. Pull the merge commit locally or tag via the GitHub UI:
```bash
git checkout main
git pull origin main

# Create an annotated tag on the merge commit
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

9) Ensure the release is marked as "Latest" on GitHub:

This is critical so users (and the `update` command) can find the new version.

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes --latest
```

CI will:
- Validate lint + tests on main and PRs
- Optional: On tag push `v*`, create a GitHub Release (but might not mark it as latest)

## Post-release verification

Install and smoke-test the CLI from the tag:
```bash
uv tool install --force git+https://github.com/dlg0/times-tables@vX.Y.Z
austimes-tables --help
```

## Troubleshooting

- CI formatting failures: run `ruff format .` locally and re-commit.
- CI lint failures: run `ruff check . --fix` and re-commit.
- Windows-newline issues: ensure repo uses LF in committed files; the formatter enforces LF for source files.
