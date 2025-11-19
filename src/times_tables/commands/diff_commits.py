"""Diff Commits command - orchestrates diffing between two git commits."""

import subprocess
import sys
import tempfile
from pathlib import Path

from times_tables.commands.extract import extract_deck
from times_tables.commands.report import generate_report


def diff_commits(
    repo_root: str = ".",
    base_ref: str = "HEAD~1",
    head_ref: str = "HEAD",
    output: str = "deck-diff.html",
    limit_rows: int = 2000,
) -> int:
    """Generate HTML diff report between two git commits.

    Args:
        repo_root: Path to git repository root
        base_ref: Base commit reference (default: HEAD~1)
        head_ref: Head commit reference (default: HEAD)
        output: Output HTML file path
        limit_rows: Maximum rows to show in detailed diff

    Returns:
        0 on success, 1 on error
    """
    root = Path(repo_root).resolve()

    # Verify it's a git repo
    if not (root / ".git").exists():
        print(f"Error: {root} is not a git repository", file=sys.stderr)
        return 1

    print(f"Generating diff report: {base_ref} -> {head_ref}")

    # Get changed files
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, head_ref],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        changed_files = [f for f in result.stdout.splitlines() if f.strip()]

        # Filter for Excel files
        excel_files = [f for f in changed_files if f.lower().endswith((".xlsx", ".xls"))]

        if not excel_files:
            print("No Excel files changed between commits.")
            # Generate a simple "No changes" report without extraction
            out_path = (root / output).resolve()
            # Create a minimal empty report
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <title>VEDA Deck Diff Report</title>
    <style>
        body {{
            font-family: -apple-system, sans-serif;
            padding: 40px;
            text-align: center;
            color: #666;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #f9f9f9;
            padding: 40px;
            border-radius: 8px;
        }}
        h1 {{ color: #333; }}
    </style>
    </head>
    <body>
    <div class="container">
        <h1>No Changes Detected</h1>
        <p>No Excel files were modified in this commit.</p>
        <p><small>Commit range: {base_ref} &rarr; {head_ref}</small></p>
    </div>
    </body>
    </html>
    """)
            return 0
    except subprocess.CalledProcessError as e:
        print(f"Error getting changed files: {e.stderr}", file=sys.stderr)
        return 1

    print(f"Found {len(excel_files)} changed Excel files.")

    # Create temp directory for worktrees
    with tempfile.TemporaryDirectory(prefix="times-tables-diff-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        base_dir = tmpdir / "base"
        head_dir = tmpdir / "head"

        def run_git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

        try:
            print(f"Checking out {base_ref} to temporary worktree...")
            run_git("worktree", "add", "--detach", "--force", str(base_dir), base_ref)

            print(f"Checking out {head_ref} to temporary worktree...")
            run_git("worktree", "add", "--detach", "--force", str(head_dir), head_ref)

            # Extract only changed files in base worktree
            print("Extracting base version...")
            extract_deck(str(base_dir), verbose=False, files=excel_files)

            # Extract only changed files in head worktree
            print("Extracting head version...")
            extract_deck(str(head_dir), verbose=False, files=excel_files)

            # Generate report
            out_path = (root / output).resolve()
            print(f"Generating report at {out_path}...")

            return generate_report(
                deck_a=str(base_dir),
                deck_b=str(head_dir),
                output=str(out_path),
                limit_rows=limit_rows,
            )

        except Exception as e:
            print(f"Error during diff process: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            return 1

        finally:
            # Cleanup worktrees
            print("Cleaning up...")
            for wt in (base_dir, head_dir):
                if wt.exists():
                    # Force remove worktree from git's perspective
                    subprocess.run(
                        ["git", "worktree", "remove", "--force", str(wt)],
                        cwd=root,
                        capture_output=True,
                    )

            # Prune worktrees to be safe
            subprocess.run(["git", "worktree", "prune"], cwd=root, capture_output=True)
