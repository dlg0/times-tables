"""Diff command implementation - compares two deck versions."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from austimes_tables.index import TablesIndexIO
from austimes_tables.models import TablesIndex


def diff_decks(deck_a: str, deck_b: str, output: str | None = None) -> int:
    """Compute structured diff between two deck versions.

    Args:
        deck_a: Path to first deck (base)
        deck_b: Path to second deck (modified)
        output: Optional output file for diff JSON (default: stdout)

    Returns:
        0 if no differences found, 1 if differences found or errors occurred

    The diff compares:
        - Tables added (in B, not in A)
        - Tables removed (in A, not in B)
        - Tables modified (same table_id, different csv_sha256)
    """
    # Load both indexes
    try:
        index_a = _load_index(deck_a, "deck_a")
        index_b = _load_index(deck_b, "deck_b")
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    # Compute diff
    diff_result = _compute_diff(deck_a, deck_b, index_a, index_b)

    # Output diff
    if output:
        try:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(diff_result, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"✓ Diff written to {output}")
        except Exception as e:
            print(f"❌ Failed to write output: {e}", file=sys.stderr)
            return 1
    else:
        # Write to stdout
        json.dump(diff_result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    # Return exit code
    summary = diff_result["summary"]
    has_changes = summary["added"] > 0 or summary["removed"] > 0 or summary["modified"] > 0
    return 1 if has_changes else 0


def _load_index(deck_root: str, deck_name: str) -> TablesIndex:
    """Load tables_index.json from a deck.

    Args:
        deck_root: Path to deck root directory
        deck_name: Human-readable deck identifier for error messages

    Returns:
        Loaded TablesIndex

    Raises:
        FileNotFoundError: If tables_index.json doesn't exist
        Exception: If the file is invalid
    """
    deck_path = Path(deck_root).resolve()
    index_path = deck_path / "shadow" / "meta" / "tables_index.json"

    if not index_path.exists():
        raise FileNotFoundError(
            f"{deck_name}: tables_index.json not found at {index_path}\n"
            "   Run 'austimes-tables extract' first"
        )

    try:
        return TablesIndexIO.read(str(index_path))
    except Exception as e:
        raise Exception(f"{deck_name}: Failed to read tables_index.json: {e}")


def _compute_diff(
    deck_a: str, deck_b: str, index_a: TablesIndex, index_b: TablesIndex
) -> dict[str, Any]:
    """Compute structured diff between two table indexes.

    Args:
        deck_a: Path to first deck (for metadata)
        deck_b: Path to second deck (for metadata)
        index_a: TablesIndex for deck A
        index_b: TablesIndex for deck B

    Returns:
        Structured diff dictionary with added/removed/modified tables
    """
    # Get table sets
    tables_a = set(index_a.tables.keys())
    tables_b = set(index_b.tables.keys())

    # Compute set differences
    added = sorted(tables_b - tables_a)
    removed = sorted(tables_a - tables_b)
    common = sorted(tables_a & tables_b)

    # Find modified tables (same table_id, different csv_sha256)
    modified = []
    unchanged = []

    for table_id in common:
        table_a = index_a.tables[table_id]
        table_b = index_b.tables[table_id]

        if table_a.csv_sha256 != table_b.csv_sha256:
            modified.append(
                {
                    "table_id": table_id,
                    "changes": {
                        "row_count": {"a": table_a.row_count, "b": table_b.row_count},
                        "csv_hash": {"a": table_a.csv_sha256, "b": table_b.csv_sha256},
                    },
                }
            )
        else:
            unchanged.append(table_id)

    # Build diff structure
    return {
        "deck_a": str(Path(deck_a).resolve()),
        "deck_b": str(Path(deck_b).resolve()),
        "compared_at": datetime.utcnow().isoformat() + "Z",
        "tables_added": added,
        "tables_removed": removed,
        "tables_modified": modified,
        "summary": {
            "total_tables_a": len(index_a.tables),
            "total_tables_b": len(index_b.tables),
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "unchanged": len(unchanged),
        },
    }
