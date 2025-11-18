"""Command-line interface for austimes-tables."""

import argparse
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

__version__ = "0.1.1"

console = Console()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="austimes-tables",
        description="Git-friendly CLI for extracting, validating, and diffing VEDA-TIMES tables",
        epilog="For detailed documentation, see: https://github.com/austimes/times-tables",
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
  austimes-tables extract /path/to/deck_root

  # Extract with custom output directory
  austimes-tables extract /path/to/deck_root --output-dir=export

  # Extract with verbose output (shows per-table progress)
  austimes-tables extract /path/to/deck_root -v

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
  austimes-tables format /path/to/deck_root

  # Recommended before committing to Git
  austimes-tables format . && git add shadow/

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
  austimes-tables validate /path/to/deck_root

  # Use in CI (exit code 0=valid, 1=errors)
  if austimes-tables validate deck/; then
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
  austimes-tables diff base_deck/ modified_deck/

  # Save diff to file
  austimes-tables diff base_deck/ modified_deck/ --output diff.json

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
  austimes-tables report base_deck/ modified_deck/ --output diff.html

  # Limit detailed row output for large diffs
  austimes-tables report base_deck/ modified_deck/ --output diff.html --limit-rows 5000

Report features (Phase 1):
  - Deck summary (changed workbooks/tables counts)
  - Table-level changes (added/removed/modified)
  - Color-coded sections
  - Self-contained (inline CSS, no external dependencies)

Note: Phase 1 implementation. Row-level diff visualization planned for Phase 2.
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Import command handlers
    if args.command == "extract":
        from austimes_tables.commands.extract import extract_deck

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
            console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
            if args.verbose:
                import traceback

                traceback.print_exc()
            return 1
    elif args.command == "format":
        from austimes_tables.commands.format import format_deck

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[RichHandler(console=console, show_time=False, show_path=False)],
        )

        return format_deck(args.deck_root)
    elif args.command == "validate":
        from austimes_tables.commands.validate import validate_deck

        return validate_deck(args.deck_root)
    elif args.command == "diff":
        from austimes_tables.commands.diff import diff_decks

        return diff_decks(args.deck_a, args.deck_b, args.output)
    elif args.command == "report":
        from austimes_tables.commands.report import generate_report

        return generate_report(args.deck_a, args.deck_b, args.output, args.limit_rows)

    return 0


if __name__ == "__main__":
    sys.exit(main())
