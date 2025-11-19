"""Generate HTML diff report between two decks."""

import csv
import json
import sys
from pathlib import Path
from typing import Any

from ..index import TablesIndexIO
from ..models import TableMeta
from ..veda import VedaSchema


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


def normalize_row_for_comparison(
    row: list[str], columns: list[str], primary_keys: list[str], tag_type: str, schema: VedaSchema
) -> list[str]:
    """Normalize a row by stripping row_ignore_symbols from primary key columns.

    This allows rows that differ only by comment markers (\\I:, *) to be
    matched as the same row during diff comparison.

    Args:
        row: Data row
        columns: Column names
        primary_keys: List of primary key column names
        tag_type: VEDA tag type (e.g., 'uc_t')
        schema: VedaSchema instance

    Returns:
        Normalized row with comment markers stripped from PK columns
    """
    normalized = row.copy()

    for i, col_name in enumerate(columns):
        # Only normalize primary key columns
        if col_name not in primary_keys:
            continue

        # Get row_ignore_symbols for this field
        ignore_symbols = schema.get_row_ignore_symbols(tag_type, col_name)
        if not ignore_symbols:
            continue

        # Strip ignore symbols from the cell value
        if i < len(normalized) and normalized[i]:
            cell_value = normalized[i]
            for symbol in ignore_symbols:
                if cell_value.startswith(symbol):
                    # Strip the symbol and any following whitespace
                    normalized[i] = cell_value[len(symbol) :].lstrip()
                    break

    return normalized


def read_table_data(
    deck_path: Path, table: TableMeta, limit_rows: int, normalize_for_diff: bool = False
) -> dict[str, Any] | None:
    """Read table data from CSV.

    Note: table.csv_path is relative to the deck's shadow directory (deck_root/shadow).

    Args:
        deck_path: Path to deck root
        table: Table metadata
        limit_rows: Maximum rows to read
        normalize_for_diff: If True, normalize PK columns by stripping row_ignore_symbols

    Returns:
        Dict with 'columns', 'rows', and optionally 'rows_normalized'
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

            result = {"columns": header, "rows": rows}

            # Add normalized rows for diff comparison if requested
            if normalize_for_diff and table.primary_keys:
                schema = VedaSchema()
                rows_normalized = [
                    normalize_row_for_comparison(
                        row, header, table.primary_keys, table.tag_type, schema
                    )
                    for row in rows
                ]
                result["rows_normalized"] = rows_normalized

            return result
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

        # For modified tables, use normalization to handle comment markers
        normalize = type_ == "modified"

        if type_ in ("removed", "modified"):
            table = index_a.tables[key]
            base_data = read_table_data(
                deck_a_path, table, limit_rows, normalize_for_diff=normalize
            )

        if type_ in ("added", "modified"):
            table = index_b.tables[key]
            current_data = read_table_data(
                deck_b_path, table, limit_rows, normalize_for_diff=normalize
            )

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
        .stacked-view {{
            display: flex;
            flex-direction: column;
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

        /* No text wrapping in table cells */
        .data-table {{
            border-collapse: collapse;
            table-layout: fixed; /* helps with explicit column widths */
            width: 100%;
        }}

        .data-table th,
        .data-table td {{
            padding: 4px 8px;
            white-space: nowrap;       /* no wrapping */
            overflow: hidden;          /* prevents overflow when narrowed */
            text-overflow: ellipsis;   /* optional: show "…" when content is clipped */
            min-height: 1.5em;         /* ensure some row height */
        }}

        /* Ellipsis rows for skipped blocks */
        .data-table .ellipsis-row td {{
            text-align: center;
            font-style: italic;
            color: #666;
            background-color: #f0f0f0;
        }}

        /* Resize grip on right edge of each header cell */
        .data-table th {{
            position: relative;
        }}

        .data-table th .col-resizer {{
            position: absolute;
            right: 0;
            top: 0;
            width: 6px;
            height: 100%;
            cursor: col-resize;
            user-select: none;
        }}

        /* Optional: visible grip */
        .data-table th .col-resizer::after {{
            content: '';
            position: absolute;
            left: 2px;
            top: 15%;
            width: 2px;
            height: 70%;
            background-color: rgba(0,0,0,0.2);
        }}
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
            html_parts.append(render_table_item(table_key, "modified", table_b, changes_str))
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

            function makeColumnsResizable(table) {
                const ths = table.querySelectorAll('thead th');
                if (!ths.length) return;

                let startX, startWidth, currentTh;

                function onMouseMove(e) {
                    if (!currentTh) return;
                    const dx = e.pageX - startX;
                    const newWidth = Math.max(40, startWidth + dx); // minimum width
                    currentTh.style.width = newWidth + 'px';

                    // Apply the same width to all cells in this column
                    const index = Array.prototype.indexOf.call(
                        currentTh.parentElement.children,
                        currentTh
                    );
                    table.querySelectorAll('tr').forEach(row => {
                        const cell = row.children[index];
                        if (cell && cell !== currentTh) {
                            cell.style.width = newWidth + 'px';
                        }
                    });
                }

                function onMouseUp() {
                    currentTh = null;
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                }

                ths.forEach(th => {
                    th.style.position = 'relative';

                    const resizer = document.createElement('div');
                    resizer.className = 'col-resizer';
                    th.appendChild(resizer);

                    resizer.addEventListener('mousedown', (e) => {
                        e.preventDefault();
                        currentTh = th;
                        startX = e.pageX;
                        startWidth = th.offsetWidth;
                        document.addEventListener('mousemove', onMouseMove);
                        document.addEventListener('mouseup', onMouseUp);
                    });
                });
            }

            function renderCompareView(container, data, mode) {
                const wrapper = document.createElement('div');
                // Determine class based on mode
                wrapper.className = (mode === 'side-by-side') ? 'side-by-side' : 'stacked-view';

                // Fallback if we don't have both (e.g. added or removed table)
                // In this case, just render what we have without diff logic.
                if (!data.base || !data.current) {
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
                    return;
                }

                const leftPanel = document.createElement('div');
                leftPanel.className = 'panel';
                leftPanel.innerHTML = '<h4>Base</h4>';

                const rightPanel = document.createElement('div');
                rightPanel.className = 'panel';
                rightPanel.innerHTML = '<h4>Current</h4>';

                const leftTable = document.createElement('table');
                leftTable.className = 'data-table';
                const rightTable = document.createElement('table');
                rightTable.className = 'data-table';

                // --- headers ---
                const leftThead = document.createElement('thead');
                const leftHeadRow = document.createElement('tr');
                data.base.columns.forEach(col => {
                    const th = document.createElement('th');
                    th.textContent = col;
                    leftHeadRow.appendChild(th);
                });
                leftThead.appendChild(leftHeadRow);
                leftTable.appendChild(leftThead);

                const rightThead = document.createElement('thead');
                const rightHeadRow = document.createElement('tr');
                data.current.columns.forEach(col => {
                    const th = document.createElement('th');
                    th.textContent = col;
                    rightHeadRow.appendChild(th);
                });
                rightThead.appendChild(rightHeadRow);
                rightTable.appendChild(rightThead);

                const leftTbody = document.createElement('tbody');
                const rightTbody = document.createElement('tbody');

                // --- daff alignment ---
                // Use normalized rows for comparison if available (to handle comment markers)
                const baseRows = data.base.rows_normalized || data.base.rows;
                const currentRows = data.current.rows_normalized || data.current.rows;

                const table1 = new daff.TableView([data.base.columns, ...baseRows]);
                const table2 = new daff.TableView([data.current.columns, ...currentRows]);

                const alignment = daff.compareTables(table1, table2).align();
                const ordering = alignment.toOrder();
                const units = ordering.getList();  // array of { l, r, p }

                const baseColCount = data.base.columns.length;
                const currColCount = data.current.columns.length;
                const maxCols = Math.max(baseColCount, currColCount);

                // ---- 1) Detect changed rows at the unit level ----
                const changedIndices = new Array(units.length).fill(false);

                for (let i = 0; i < units.length; i++) {
                    const { l, r } = units[i];

                    // Skip header alignments
                    if (l === 0 || r === 0) continue;

                    const baseRow = (l > 0 && data.base.rows[l - 1])
                        ? data.base.rows[l - 1]
                        : null;
                    const currRow = (r > 0 && data.current.rows[r - 1])
                        ? data.current.rows[r - 1]
                        : null;

                    let isChanged = false;

                    if ((baseRow && !currRow) || (!baseRow && currRow)) {
                        // pure add / delete
                        isChanged = true;
                    } else if (baseRow && currRow) {
                        // compare cell-by-cell; also treat column-count changes as changes
                        const colsToCheck = Math.max(
                            baseRow.length,
                            currRow.length,
                            baseColCount,
                            currColCount
                        );
                        for (let c = 0; c < colsToCheck; c++) {
                            const baseVal = (c < baseRow.length) ? baseRow[c] : '';
                            const currVal = (c < currRow.length) ? currRow[c] : '';
                            if (baseVal !== currVal) {
                                isChanged = true;
                                break;
                            }
                        }
                    }

                    if (isChanged) {
                        changedIndices[i] = true;
                    }
                }

                // ---- 2) Add context around changed rows ----
                const CONTEXT_RADIUS = 2;
                const toShow = new Array(units.length).fill(false);

                for (let i = 0; i < units.length; i++) {
                    if (!changedIndices[i]) continue;
                    const start = Math.max(0, i - CONTEXT_RADIUS);
                    const end = Math.min(units.length - 1, i + CONTEXT_RADIUS);
                    for (let j = start; j <= end; j++) {
                        toShow[j] = true;
                    }
                }

                // ---- 3) Render only marked units, inserting "..." for gaps ----
                let lastShownIndex = -1;

                for (let i = 0; i < units.length; i++) {
                    const unit = units[i];
                    const l = unit.l;
                    const r = unit.r;

                    // Skip header alignments; do not show them or use them as content rows
                    if (l === 0 || r === 0) continue;
                    if (!toShow[i]) continue;

                    // If there is a gap from the last shown content row, insert "..." rows
                    if (lastShownIndex >= 0 && i > lastShownIndex + 1) {
                        const leftEllipsisTr = document.createElement('tr');
                        const rightEllipsisTr = document.createElement('tr');
                        leftEllipsisTr.classList.add('ellipsis-row');
                        rightEllipsisTr.classList.add('ellipsis-row');

                        const leftTd = document.createElement('td');
                        leftTd.colSpan = baseColCount;
                        leftTd.textContent = '…';

                        const rightTd = document.createElement('td');
                        rightTd.colSpan = currColCount;
                        rightTd.textContent = '…';

                        leftEllipsisTr.appendChild(leftTd);
                        rightEllipsisTr.appendChild(rightTd);
                        leftTbody.appendChild(leftEllipsisTr);
                        rightTbody.appendChild(rightEllipsisTr);
                    }

                    const baseRow = (l > 0 && data.base.rows[l - 1])
                        ? data.base.rows[l - 1]
                        : null;
                    const currRow = (r > 0 && data.current.rows[r - 1])
                        ? data.current.rows[r - 1]
                        : null;

                    const leftTr = document.createElement('tr');
                    const rightTr = document.createElement('tr');

                    // Row-level add/delete highlighting
                    if (baseRow && !currRow) {
                        leftTr.classList.add('daff-del');
                    } else if (!baseRow && currRow) {
                        rightTr.classList.add('daff-add');
                    }

                    for (let c = 0; c < maxCols; c++) {
                        const baseVal = baseRow && c < baseRow.length ? baseRow[c] : '';
                        const currVal = currRow && c < currRow.length ? currRow[c] : '';

                        const tdLeft = document.createElement('td');
                        const tdRight = document.createElement('td');

                        // Use non-breaking space for empty cells so rows keep height
                        tdLeft.textContent = baseVal || '\u00a0';
                        tdRight.textContent = currVal || '\u00a0';

                        const baseHasCol = c < baseColCount;
                        const currHasCol = c < currColCount;

                        if (baseRow && !currRow) {
                            tdLeft.classList.add('daff-del');
                        } else if (!baseRow && currRow) {
                            tdRight.classList.add('daff-add');
                        } else if (baseHasCol && !currHasCol) {
                            tdLeft.classList.add('daff-del');
                        } else if (!baseHasCol && currHasCol) {
                            tdRight.classList.add('daff-add');
                        } else if (baseRow && currRow && baseVal !== currVal) {
                            tdLeft.classList.add('daff-mod');
                            tdRight.classList.add('daff-mod');
                        }

                        leftTr.appendChild(tdLeft);
                        rightTr.appendChild(tdRight);
                    }

                    leftTbody.appendChild(leftTr);
                    rightTbody.appendChild(rightTr);

                    lastShownIndex = i;
                }

                leftTable.appendChild(leftTbody);
                rightTable.appendChild(rightTbody);

                // Enable column resizing on both tables
                makeColumnsResizable(leftTable);
                makeColumnsResizable(rightTable);

                leftPanel.appendChild(leftTable);
                rightPanel.appendChild(rightTable);

                wrapper.appendChild(leftPanel);
                wrapper.appendChild(rightPanel);
                container.appendChild(wrapper);
            }

            function renderView(container, key, mode) {
                container.innerHTML = '';
                const data = tableData[key];
                if (!data) {
                    container.textContent = 'Error loading data.';
                    return;
                }

                if (mode === 'side-by-side' || mode === 'stacked') {
                    renderCompareView(container, data, mode);
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
                    // Use normalized rows for comparison if available (to handle comment markers)
                    const baseRows = data.base.rows_normalized || data.base.rows;
                    const currentRows = data.current.rows_normalized || data.current.rows;

                    const table1 = new daff.TableView([data.base.columns, ...baseRows]);
                    const table2 = new daff.TableView([data.current.columns, ...currentRows]);

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
