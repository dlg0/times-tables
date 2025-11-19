"""VEDA tag scanner for workbooks.

Discovers all VEDA tables in a workbook and extracts metadata.
"""

from typing import Any

from openpyxl import Workbook

from times_tables import excel


def scan_workbook(workbook: Workbook) -> list[dict[str, Any]]:
    """Scan workbook for VEDA tags and extract table metadata.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of table metadata dictionaries with keys:
            - tag: str - Full tag string (e.g., '~FI_T: BaseParameters')
            - tag_type: str - Normalized tag type (e.g., 'fi_t')
            - logical_name: str | None - Logical name if present
            - sheet_name: str - Sheet name containing the table
            - tag_row: int - Row number of tag (1-indexed)
            - tag_col: int - Column number of tag (1-indexed)
            - headers: list[str] - Column headers
            - row_count: int - Number of data rows

    Raises:
        FileNotFoundError: If workbook file doesn't exist
    """
    tables = []

    for sheet_name in excel.get_sheet_names(workbook):
        sheet = workbook[sheet_name]
        tags = excel.find_tags(sheet)

        # Build set of tag columns for each row to detect table boundaries
        tag_positions = {}
        for tag_info in tags:
            row = tag_info["row"]
            if row not in tag_positions:
                tag_positions[row] = set()
            tag_positions[row].add(tag_info["col"])

        for tag_info in tags:
            # Parse tag to extract tag_type and logical_name
            tag_value = tag_info["value"]
            tag_type, logical_name = _parse_tag(tag_value)

            # Extract headers and data rows with boundary detection
            tag_row = tag_info["row"]
            tag_col = tag_info["col"]

            # Find other tags on same row to determine boundaries
            other_tags_on_row = tag_positions.get(tag_row, set()) - {tag_col}

            headers, data_rows = _read_table_with_boundaries(
                sheet, start_row=tag_row, start_col=tag_col, other_tag_cols=other_tags_on_row
            )

            # Build table metadata dictionary
            table_dict = {
                "tag": tag_value,
                "tag_type": tag_type,
                "logical_name": logical_name,
                "sheet_name": sheet_name,
                "tag_row": tag_row,
                "tag_col": tag_col,
                "headers": headers,
                "row_count": len(data_rows),
            }

            tables.append(table_dict)

    return tables


def _read_table_with_boundaries(
    sheet, start_row: int, start_col: int, other_tag_cols: set[int]
) -> tuple[list[str], list[list[Any]]]:
    """Read table headers and data, respecting boundaries from other tags.

    Args:
        sheet: openpyxl Worksheet object
        start_row: Tag row (headers are at start_row + 1)
        start_col: Tag column (leftmost column, may be adjusted)
        other_tag_cols: Set of column indices that have tags on the same row

    Returns:
        (headers, data_rows) where:
        - headers: list of header strings
        - data_rows: list of data row lists
    """
    header_row_idx = start_row + 1
    data_start_row = start_row + 2

    # If the tag column has no header, scan right to find where headers start
    # This handles cases where the tag is to the left of the actual table
    actual_start_col = start_col
    if sheet.cell(row=header_row_idx, column=start_col).value is None:
        # Scan right to find first non-None header, up to max reasonable distance
        for col in range(start_col + 1, start_col + 10):
            if sheet.cell(row=header_row_idx, column=col).value is not None:
                actual_start_col = col
                break

    # Read headers, stopping at None or another tag column
    headers = []
    col_idx = actual_start_col
    while True:
        # Stop if we've reached another table's tag column
        if col_idx in other_tag_cols:
            break

        cell_value = sheet.cell(row=header_row_idx, column=col_idx).value
        if cell_value is None:
            break
        headers.append(str(cell_value).strip())
        col_idx += 1

    if not headers:
        return [], []

    num_cols = len(headers)

    # Read data rows
    data_rows = []
    row_idx = data_start_row

    while row_idx <= sheet.max_row:
        # Read current row
        row_data = []
        is_empty = True

        for col_offset in range(num_cols):
            cell_value = sheet.cell(row=row_idx, column=actual_start_col + col_offset).value
            row_data.append(cell_value)
            if cell_value is not None:
                is_empty = False

        # Stop at first completely empty row
        if is_empty:
            break

        data_rows.append(row_data)
        row_idx += 1

    return headers, data_rows


def _parse_tag(tag: str) -> tuple[str, str | None]:
    """Parse VEDA tag to extract tag type and logical name.

    Args:
        tag: Full tag string (e.g., '~FI_T: BaseParameters')

    Returns:
        Tuple of (tag_type, logical_name)
        - tag_type: Normalized lowercase tag type without ~ prefix
        - logical_name: Logical name if present, None otherwise
    """
    # Remove ~ prefix
    tag_stripped = tag.lstrip("~").strip()

    # Split on colon
    if ":" in tag_stripped:
        parts = tag_stripped.split(":", 1)
        tag_type = parts[0].strip().lower()
        logical_name = parts[1].strip() if len(parts) > 1 else None
    else:
        tag_type = tag_stripped.strip().lower()
        logical_name = None

    return tag_type, logical_name
