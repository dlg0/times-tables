"""Generate HTML diff report between two decks."""

import sys
from pathlib import Path

from ..index import TablesIndexIO


def generate_report(deck_a: str, deck_b: str, output: str, limit_rows: int = 2000) -> int:
    """Generate HTML diff report between two decks.

    Args:
        deck_a: Path to first deck (base)
        deck_b: Path to second deck (modified)
        output: Output HTML file path
        limit_rows: Maximum rows to show in detailed diff (default: 2000)

    Returns:
        0 on success, 1 on error
    """
    try:
        # Load deck indexes
        index_a_path = Path(deck_a) / "shadow" / "meta" / "tables_index.json"
        index_b_path = Path(deck_b) / "shadow" / "meta" / "tables_index.json"

        if not index_a_path.exists():
            print(f"Error: {index_a_path} not found. Run 'extract' first.", file=sys.stderr)
            return 1

        if not index_b_path.exists():
            print(f"Error: {index_b_path} not found. Run 'extract' first.", file=sys.stderr)
            return 1

        index_a = TablesIndexIO.read(str(index_a_path))
        index_b = TablesIndexIO.read(str(index_b_path))

        # Compute diff
        diff_result = compute_diff(index_a, index_b)

        # Generate HTML
        html = generate_html(deck_a, deck_b, diff_result, limit_rows)

        # Write output
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✓ Generated report: {output}")
        return 0

    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


def compute_diff(index_a, index_b):
    """Compute diff between two deck indexes.

    Returns:
        dict with keys: added, removed, modified, unchanged
    """
    tables_a = set(index_a.tables.keys())
    tables_b = set(index_b.tables.keys())

    added = sorted(tables_b - tables_a)
    removed = sorted(tables_a - tables_b)
    common = sorted(tables_a & tables_b)

    modified = []
    unchanged = []

    for table_key in common:
        table_a = index_a.tables[table_key]
        table_b = index_b.tables[table_key]

        # Compare CSV hashes to detect modifications
        if table_a.csv_sha256 != table_b.csv_sha256:
            modified.append(table_key)
        else:
            unchanged.append(table_key)

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
        "index_a": index_a,
        "index_b": index_b,
    }


def generate_html(deck_a: str, deck_b: str, diff_result: dict, limit_rows: int) -> str:
    """Generate HTML report from diff results.

    Args:
        deck_a: Path to first deck
        deck_b: Path to second deck
        diff_result: Diff computation result
        limit_rows: Maximum rows to show (currently unused in Phase 1)

    Returns:
        HTML string
    """
    added = diff_result["added"]
    removed = diff_result["removed"]
    modified = diff_result["modified"]
    unchanged = diff_result["unchanged"]
    index_a = diff_result["index_a"]
    index_b = diff_result["index_b"]

    # Build HTML
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VEDA Deck Diff Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .summary {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .summary ul {
            list-style: none;
            padding: 0;
        }
        .summary li {
            padding: 8px 0;
            border-bottom: 1px solid #dee2e6;
        }
        .summary li:last-child {
            border-bottom: none;
        }
        .stat {
            font-weight: bold;
            margin-right: 10px;
        }
        .added { color: #28a745; }
        .removed { color: #dc3545; }
        .modified { color: #ffc107; }
        .unchanged { color: #6c757d; }
        .deck-info {
            font-family: monospace;
            background: #e9ecef;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        .table-list {
            margin: 10px 0;
        }
        .table-item {
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            border-radius: 3px;
            font-family: monospace;
            font-size: 0.9em;
        }
        .table-item.added {
            border-left-color: #28a745;
            background: #d4edda;
        }
        .table-item.removed {
            border-left-color: #dc3545;
            background: #f8d7da;
        }
        .table-item.modified {
            border-left-color: #ffc107;
            background: #fff3cd;
        }
        .details-section {
            margin-top: 30px;
        }
        .no-changes {
            color: #6c757d;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>VEDA Deck Comparison</h1>
""")

    # Summary section
    deck_a_html = escape_html(deck_a)
    deck_b_html = escape_html(deck_b)
    html_parts.append(f"""
        <div class="summary">
            <h2>Summary</h2>
            <p>Compared: <span class="deck-info">{deck_a_html}</span> vs \
<span class="deck-info">{deck_b_html}</span></p>
            <ul>
                <li><span class="stat added">Added:</span> {len(added)} table(s)</li>
                <li><span class="stat removed">Removed:</span> {len(removed)} table(s)</li>
                <li><span class="stat modified">Modified:</span> {len(modified)} table(s)</li>
                <li><span class="stat unchanged">Unchanged:</span> {len(unchanged)} table(s)</li>
            </ul>
        </div>
""")

    # Details section
    html_parts.append("""
        <div class="details-section">
            <h2>Details</h2>
""")

    # Added tables
    if added:
        html_parts.append("""
            <h3 class="added">Added Tables</h3>
            <div class="table-list">
""")
        for table_key in added:
            table = index_b.tables[table_key]
            key_html = escape_html(table_key)
            sheet_html = escape_html(table.sheet_name)
            tag_html = escape_html(table.tag)
            html_parts.append(f"""
                <div class="table-item added">
                    <strong>{key_html}</strong><br>
                    Sheet: {sheet_html} | Tag: {tag_html} | Rows: {table.row_count}
                </div>
""")
        html_parts.append("            </div>\n")

    # Removed tables
    if removed:
        html_parts.append("""
            <h3 class="removed">Removed Tables</h3>
            <div class="table-list">
""")
        for table_key in removed:
            table = index_a.tables[table_key]
            key_html = escape_html(table_key)
            sheet_html = escape_html(table.sheet_name)
            tag_html = escape_html(table.tag)
            html_parts.append(f"""
                <div class="table-item removed">
                    <strong>{key_html}</strong><br>
                    Sheet: {sheet_html} | Tag: {tag_html} | Rows: {table.row_count}
                </div>
""")
        html_parts.append("            </div>\n")

    # Modified tables
    if modified:
        html_parts.append("""
            <h3 class="modified">Modified Tables</h3>
            <div class="table-list">
""")
        for table_key in modified:
            table_a = index_a.tables[table_key]
            table_b = index_b.tables[table_key]
            row_diff = table_b.row_count - table_a.row_count
            row_diff_str = (
                f"(+{row_diff})"
                if row_diff > 0
                else f"({row_diff})"
                if row_diff < 0
                else "(no change)"
            )

            html_parts.append(f"""
                <div class="table-item modified">
                    <strong>{escape_html(table_key)}</strong><br>
                    Sheet: {escape_html(table_b.sheet_name)} | Tag: {escape_html(table_b.tag)}<br>
                    Rows: {table_a.row_count} → {table_b.row_count} {row_diff_str}
                </div>
""")
        html_parts.append("            </div>\n")

    # No changes message
    if not added and not removed and not modified:
        html_parts.append("""
            <p class="no-changes">No changes detected between the two decks.</p>
""")

    html_parts.append("""
        </div>
    </div>
</body>
</html>
""")

    return "".join(html_parts)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
