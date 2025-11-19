"""Generate HTML diff report between two decks."""

import csv
import json
import sys
from pathlib import Path
from typing import Any

from ..index import TablesIndexIO
from ..models import TableMeta


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

        # Load daff.js
        daff_path = Path(__file__).parent.parent / "static" / "daff.js"
        daff_js = ""
        if daff_path.exists():
            with open(daff_path, "r", encoding="utf-8") as f:
                daff_js = f.read()
        else:
            print(
                f"Warning: daff.js not found at {daff_path}. Diff view will not work.",
                file=sys.stderr,
            )

        # Generate HTML
        html = generate_html(deck_a, deck_b, diff_result, limit_rows, daff_js)

        # Write outpu
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


def read_table_data(deck_path: Path, table: TableMeta, limit_rows: int) -> dict[str, Any] | None:
    """Read table data from CSV.

    Note: table.csv_path is relative to the deck's shadow directory (deck_root/shadow).
    """
    shadow_dir = deck_path / "shadow"
    csv_path = shadow_dir / table.csv_path
    if not csv_path.exists():
        return None

    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                header = []

            rows = []
            for i, row in enumerate(reader):
                if i >= limit_rows:
                    break
                rows.append(row)
            return {"columns": header, "rows": rows}
    except Exception:
        return None


def generate_html(
    deck_a: str, deck_b: str, diff_result: dict, limit_rows: int, daff_js: str
) -> str:
    """Generate HTML report from diff results.

    Args:
        deck_a: Path to first deck
        deck_b: Path to second deck
        diff_result: Diff computation resul
        limit_rows: Maximum rows to show
        daff_js: Content of daff.js library

    Returns:
        HTML string
    """
    added = diff_result["added"]
    removed = diff_result["removed"]
    modified = diff_result["modified"]
    unchanged = diff_result["unchanged"]
    index_a = diff_result["index_a"]
    index_b = diff_result["index_b"]

    deck_a_path = Path(deck_a)
    deck_b_path = Path(deck_b)

    # Prepare table data dictionary
    table_data = {}

    # Helper to add data
    def add_data(key, type_):
        base_data = None
        current_data = None

        if type_ in ("removed", "modified"):
            table = index_a.tables[key]
            base_data = read_table_data(deck_a_path, table, limit_rows)

        if type_ in ("added", "modified"):
            table = index_b.tables[key]
            current_data = read_table_data(deck_b_path, table, limit_rows)

        table_data[key] = {"base": base_data, "current": current_data, "type": type_}

    for key in added:
        add_data(key, "added")
    for key in removed:
        add_data(key, "removed")
    for key in modified:
        add_data(key, "modified")

    # Build HTML
    html_parts = []
    html_parts.append(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VEDA Deck Diff Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .summary {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary ul {{
            list-style: none;
            padding: 0;
        }}
        .summary li {{
            padding: 8px 0;
            border-bottom: 1px solid #dee2e6;
        }}
        .stat {{
            font-weight: bold;
            margin-right: 10px;
        }}
        .added {{ color: #28a745; }}
        .removed {{ color: #dc3545; }}
        .modified {{ color: #ffc107; }}
        .unchanged {{ color: #6c757d; }}

        .table-item {{
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            border-radius: 3px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .table-item:hover {{
            background: #e9ecef;
        }}
        .table-item.added {{ border-left-color: #28a745; background: #d4edda; }}
        .table-item.removed {{ border-left-color: #dc3545; background: #f8d7da; }}
        .table-item.modified {{ border-left-color: #ffc107; background: #fff3cd; }}

        .details-container {{
            display: none;
            margin-top: 10px;
            border: 1px solid #ddd;
            background: white;
            padding: 10px;
        }}
        .details-container.active {{
            display: block;
        }}

        .toolbar {{
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        button {{
            padding: 5px 10px;
            margin-right: 5px;
            cursor: pointer;
            background: #fff;
            border: 1px solid #ccc;
            border-radius: 3px;
        }}
        button.active {{
            background: #007bff;
            color: white;
            border-color: #0056b3;
        }}

        .data-table {{
            border-collapse: collapse;
            width: 100%;
            font-family: monospace;
            font-size: 0.85em;
        }}
        .data-table th, .data-table td {{
            border: 1px solid #ddd;
            padding: 4px;
            text-align: left;
        }}
        .data-table th {{
            background: #f1f1f1;
            font-weight: bold;
        }}

        .side-by-side {{
            display: flex;
            gap: 20px;
        }}
        .panel {{
            flex: 1;
            overflow-x: auto;
        }}
        .panel h4 {{ margin: 0 0 10px 0; }}

        /* Daff styles */
        .daff-add {{ background-color: #d4edda; }}
        .daff-del {{ background-color: #f8d7da; text-decoration: line-through; }}
        .daff-mod {{ background-color: #fff3cd; }}
        .daff-header {{ background-color: #f1f1f1; font-weight: bold; }}
    </style>
    <script>
        {daff_js}
    </script>
    <script id="table-data" type="application/json">
        {json.dumps(table_data, ensure_ascii=False)}
    </script>
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
            <p>Compared: <span class="deck-info">{deck_a_html}</span> vs
<span class="deck-info">{deck_b_html}</span></p>
            <ul>
                <li><span class="stat added">Added:</span> {len(added)} table(s)</li>
                <li><span class="stat removed">Removed:</span> {len(removed)} table(s)</li>
                <li><span class="stat modified">Modified:</span> {len(modified)} table(s)</li>
                <li><span class="stat unchanged">Unchanged:</span> {len(unchanged)} table(s)</li>
            </ul>
        </div>

        <div class="details-section">
            <h2>Details</h2>
            <p>Click on a table to view details.</p>
""")

    def render_table_item(key, type_, table, changes_str=""):
        key_html = escape_html(key)
        sheet_html = escape_html(table.sheet_name)
        tag_html = escape_html(table.tag)
        return f"""
            <div class="table-wrapper" data-key="{key_html}">
                <div class="table-item {type_}">
                    <strong>{key_html}</strong><br>
                    Sheet: {sheet_html} | Tag: {tag_html} | {changes_str}
                </div>
                <div class="details-container">
                    <div class="toolbar">
                        <button data-mode="diff" class="active">Diff View</button>
                        <button data-mode="side-by-side">Side-by-Side</button>
                        <button data-mode="stacked">Stacked</button>
                    </div>
                    <div class="view-container"></div>
                </div>
            </div>
        """

    # Added tables
    if added:
        html_parts.append('<h3 class="added">Added Tables</h3><div class="table-list">')
        for table_key in added:
            table = index_b.tables[table_key]
            html_parts.append(
                render_table_item(table_key, "added", table, f"Rows: {table.row_count}")
            )
        html_parts.append("</div>")

    # Removed tables
    if removed:
        html_parts.append('<h3 class="removed">Removed Tables</h3><div class="table-list">')
        for table_key in removed:
            table = index_a.tables[table_key]
            html_parts.append(
                render_table_item(table_key, "removed", table, f"Rows: {table.row_count}")
            )
        html_parts.append("</div>")

    # Modified tables
    if modified:
        html_parts.append('<h3 class="modified">Modified Tables</h3><div class="table-list">')
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
            changes_str = f"Rows: {table_a.row_count} → {table_b.row_count} {row_diff_str}"
            html_parts.append(render_table_item(table_key, "modified", table, changes_str))
        html_parts.append("</div>")

    if not added and not removed and not modified:
        html_parts.append('<p class="no-changes">No changes detected between the two decks.</p>')

    # Client-side JS
    html_parts.append("""
    </div> <!-- end details-section -->
    </div> <!-- end container -->

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const tableData = JSON.parse(document.getElementById('table-data').textContent);
            const daff = window.daff;

            // Helper to render a basic HTML table
            function createTable(data) {
                if (!data) return document.createElement('div');

                const table = document.createElement('table');
                table.className = 'data-table';

                const thead = document.createElement('thead');
                const trHead = document.createElement('tr');
                data.columns.forEach(col => {
                    const th = document.createElement('th');
                    th.textContent = col;
                    trHead.appendChild(th);
                });
                thead.appendChild(trHead);
                table.appendChild(thead);

                const tbody = document.createElement('tbody');
                data.rows.forEach(row => {
                    const tr = document.createElement('tr');
                    row.forEach(cell => {
                        const td = document.createElement('td');
                        td.textContent = cell;
                        tr.appendChild(td);
                    });
                    tbody.appendChild(tr);
                });
                table.appendChild(tbody);

                return table;
            }

            function renderView(container, key, mode) {
                container.innerHTML = '';
                const data = tableData[key];
                if (!data) {
                    container.textContent = 'Error loading data.';
                    return;
                }

                if (mode === 'side-by-side') {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'side-by-side';

                    const left = document.createElement('div');
                    left.className = 'panel';
                    left.innerHTML = '<h4>Base</h4>';
                    if (data.base) left.appendChild(createTable(data.base));
                    else left.innerHTML += '<em>(Not present)</em>';

                    const right = document.createElement('div');
                    right.className = 'panel';
                    right.innerHTML = '<h4>Current</h4>';
                    if (data.current) right.appendChild(createTable(data.current));
                    else right.innerHTML += '<em>(Not present)</em>';

                    wrapper.appendChild(left);
                    wrapper.appendChild(right);
                    container.appendChild(wrapper);
                }
                else if (mode === 'stacked') {
                    const top = document.createElement('div');
                    top.className = 'panel';
                    top.innerHTML = '<h4>Base</h4>';
                    if (data.base) top.appendChild(createTable(data.base));
                    else top.innerHTML += '<em>(Not present)</em>';

                    const bottom = document.createElement('div');
                    bottom.className = 'panel';
                    bottom.style.marginTop = '20px';
                    bottom.innerHTML = '<h4>Current</h4>';
                    if (data.current) bottom.appendChild(createTable(data.current));
                    else bottom.innerHTML += '<em>(Not present)</em>';

                    container.appendChild(top);
                    container.appendChild(bottom);
                }
                else if (mode === 'diff') {
                    if (!data.base || !data.current) {
                        container.innerHTML = '<em>Diff requires both base and current tables. ' +
                            'Switch to Side-by-Side view to see single table.</em>';
                        // If only one exists, just show i
                        if (data.base) container.appendChild(createTable(data.base));
                        if (data.current) container.appendChild(createTable(data.current));
                        return;
                    }

                    // Use daff to compute diff
                    const table1 = new daff.TableView([data.base.columns, ...data.base.rows]);
                    const table2 = new daff.TableView([data.current.columns, ...data.current.rows]);

                    const alignment = daff.compareTables(table1, table2).align();
                    const dataDiff = [];
                    const tableDiff = new daff.TableView(dataDiff);

                    const flags = new daff.CompareFlags();
                    const highlighter = new daff.TableDiff(alignment, flags);
                    highlighter.hilite(tableDiff);

                    const diff2html = new daff.DiffRender();
                    diff2html.render(tableDiff);
                    const tableHtml = diff2html.html();

                    container.innerHTML = tableHtml;

                    // Add class to table
                    const tableEl = container.querySelector('table');
                    if (tableEl) tableEl.className = 'data-table daff-table';
                }
            }

            // Click handlers
            document.addEventListener('click', (e) => {
                // Toggle details
                if (e.target.closest('.table-item')) {
                    const wrapper = e.target.closest('.table-wrapper');
                    const details = wrapper.querySelector('.details-container');
                    const key = wrapper.dataset.key;

                    // Toggle active class
                    if (details.classList.contains('active')) {
                        details.classList.remove('active');
                    } else {
                        // Close others? Optional. Let's keep them open if user wants.
                        details.classList.add('active');

                        // Render default view if empty
                        const container = details.querySelector('.view-container');
                        if (!container.hasChildNodes()) {
                            renderView(container, key, 'diff');
                        }
                    }
                }

                // Switch modes
                if (e.target.matches('button[data-mode]')) {
                    const btn = e.target;
                    const wrapper = btn.closest('.table-wrapper');
                    const key = wrapper.dataset.key;
                    const container = wrapper.querySelector('.view-container');
                    const mode = btn.dataset.mode;

                    // Update buttons
                    wrapper.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');

                    renderView(container, key, mode);
                }
            });
        });
    </script>
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
