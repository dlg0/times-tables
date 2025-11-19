"""Command-line interface for times-tables."""

import argparse
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich_argparse import RichHelpFormatter

try:
    from importlib.metadata import version

    __version__ = version("times-tables")
except Exception:
    __version__ = "unknown"

console = Console()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="times-tables",
        description="Git-friendly CLI for extracting, validating, and diffing VEDA-TIMES tables",
        epilog="For detailed documentation, see: https://github.com/dlg0/times-tables",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # extract command
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract VEDA tables from Excel workbooks to CSV",
        description=(
            "Extract all VEDA tables from Excel workbooks and write canonical CSV shadow tables."
        ),
        epilog="""
Examples:
  # Extract tables to default shadow/ directory
  times-tables extract /path/to/deck_root

  # Extract with custom output directory
  times-tables extract /path/to/deck_root --output-dir=export

  # Extract with verbose output (shows per-table progress)
  times-tables extract /path/to/deck_root -v

Output structure:
  deck_root/shadow/tables/<workbook_id>/<table_id>.csv
  deck_root/shadow/meta/tables_index.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    extract_parser.add_argument(
        "deck_root", help="Path to VEDA deck root directory (scans *.xlsx and SupplXLS/*.xlsx)"
    )
    extract_parser.add_argument(
        "--output-dir",
        default="shadow",
        help="Output directory for shadow tables (default: shadow)",
    )
    extract_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (shows per-table details)",
    )

    # format command
    format_parser = subparsers.add_parser(
        "format",
        help="Re-canonicalize existing shadow CSVs",
        description=(
            "Canonicalize shadow tables: sort by primary key, apply canonical column order."
        ),
        epilog="""
Examples:
  # Ensure deterministic CSV format (idempotent, safe to run multiple times)
  times-tables format /path/to/deck_root

  # Recommended before committing to Git
  times-tables format . && git add shadow/

Purpose:
  - Sorts rows by primary key (lexicographic order)
  - Applies canonical column order from schema
  - Ensures UTF-8 encoding with LF line endings
  - Guarantees stable Git diffs across platforms
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    format_parser.add_argument("deck_root", help="Path to VEDA deck root directory")

    # validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate shadow tables against schema",
        description="Validate shadow tables against xl2times schema requirements.",
        epilog="""
Examples:
  # Validate and show errors
  times-tables validate /path/to/deck_root

  # Use in CI (exit code 0=valid, 1=errors)
  if times-tables validate deck/; then
    echo "All tables valid"
  else
    echo "Validation errors found"
    exit 1
  fi

Checks performed:
  - Required columns present
  - Primary key columns exist and non-NULL
  - No duplicate primary keys
  - Basic type safety (if exposed by xl2times)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    validate_parser.add_argument("deck_root", help="Path to VEDA deck root directory")

    # diff command
    diff_parser = subparsers.add_parser(
        "diff",
        help="Compute structured diff between two decks",
        description="Compute structured JSON diff between two deck versions.",
        epilog="""
Examples:
  # Diff to stdout
  times-tables diff base_deck/ modified_deck/

  # Save diff to file
  times-tables diff base_deck/ modified_deck/ --output diff.json

Output includes:
  - Tables added (in deck_b, not in deck_a)
  - Tables removed (in deck_a, not in deck_b)
  - Tables modified (different csv_sha256 hash)
  - Summary counts and row count changes

Exit codes:
  - 0: No differences found
  - 1: Differences found or errors occurred
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    diff_parser.add_argument("deck_a", help="Path to first deck (base)")
    diff_parser.add_argument("deck_b", help="Path to second deck (modified)")
    diff_parser.add_argument("--output", help="Output file for diff JSON (default: stdout)")

    # report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate HTML diff report",
        description="Generate self-contained HTML diff report.",
        epilog="""
Examples:
  # Generate HTML report
  times-tables report base_deck/ modified_deck/ --output diff.html

  # Limit detailed row output for large diffs
  times-tables report base_deck/ modified_deck/ --output diff.html --limit-rows 5000

Report features:
  - Deck summary (changed workbooks/tables counts)
  - Table-level changes (added/removed/modified)
  - Detailed views: Side-by-side, Stacked, and Diff (highlighted changes)
  - Self-contained (inline CSS/JS, no external dependencies)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    report_parser.add_argument("deck_a", help="Path to first deck (base)")
    report_parser.add_argument("deck_b", help="Path to second deck (modified)")
    report_parser.add_argument("--output", required=True, help="Output HTML file path")
    report_parser.add_argument(
        "--limit-rows",
        type=int,
        default=2000,
        help="Maximum rows to show in detailed diff (default: 2000)",
    )

    # diff-commits command
    diff_commits_parser = subparsers.add_parser(
        "diff-commits",
        help="Generate HTML diff report between git commits",
        description="Generate HTML diff report between two git commits using worktrees.",
        epilog="""
Examples:
  # Diff last commit against previous (default)
  times-tables diff-commits

  # Diff specific commits
  times-tables diff-commits --base-ref v1.0 --head-ref v1.1 --output report.html

  # Run in a specific repo
  times-tables diff-commits --repo-root /path/to/repo
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    diff_commits_parser.add_argument(
        "--repo-root", default=".", help="Path to git repository root (default: .)"
    )
    diff_commits_parser.add_argument(
        "--base-ref", default="HEAD~1", help="Base commit reference (default: HEAD~1)"
    )
    diff_commits_parser.add_argument(
        "--head-ref", default="HEAD", help="Head commit reference (default: HEAD)"
    )
    diff_commits_parser.add_argument(
        "--output", default="deck-diff.html", help="Output HTML file path (default: deck-diff.html)"
    )
    diff_commits_parser.add_argument(
        "--limit-rows",
        type=int,
        default=2000,
        help="Maximum rows to show in detailed diff (default: 2000)",
    )

    # update command
    update_parser = subparsers.add_parser(
        "update",
        help="Update times-tables to the latest version",
        description="Update times-tables CLI to the latest version from GitHub.",
        epilog="""
Examples:
  # Update to latest version
  times-tables update

  # Update to specific version
  times-tables update --version v0.2.0
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    update_parser.add_argument(
        "--version", help="Specific version to install (e.g., v0.2.0). Default: latest"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Import command handlers
    if args.command == "extract":
        from times_tables.commands.extract import extract_deck

        # Configure logging
        logging.basicConfig(
            level=logging.INFO if args.verbose else logging.WARNING,
            format="%(message)s",
            handlers=[RichHandler(console=console, show_time=False, show_path=False)],
        )

        try:
            index = extract_deck(args.deck_root, args.output_dir, args.verbose)
            console.print(f"[green]✓[/green] Extracted {len(index.tables)} tables")
            return 0
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            if args.verbose:
                import traceback

                traceback.print_exc()
            return 1
    elif args.command == "format":
        from times_tables.commands.format import format_deck

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[RichHandler(console=console, show_time=False, show_path=False)],
        )

        return format_deck(args.deck_root)
    elif args.command == "validate":
        from times_tables.commands.validate import validate_deck

        return validate_deck(args.deck_root)
    elif args.command == "diff":
        from times_tables.commands.diff import diff_decks

        return diff_decks(args.deck_a, args.deck_b, args.output)
    elif args.command == "report":
        from times_tables.commands.report import generate_report

        return generate_report(args.deck_a, args.deck_b, args.output, args.limit_rows)
    elif args.command == "diff-commits":
        from times_tables.commands.diff_commits import diff_commits

        return diff_commits(
            args.repo_root, args.base_ref, args.head_ref, args.output, args.limit_rows
        )
    elif args.command == "update":
        from times_tables.commands.update import update_cli

        return update_cli(args.version)

    return 0


if __name__ == "__main__":
    sys.exit(main())
