"""Stable identifier generation for workbooks and tables.

Provides deterministic, unique IDs that remain stable across workbook/sheet moves.
"""

import re


def generate_workbook_id(file_path: str) -> str:
    """Generate stable workbook_id from file path.

    Args:
        file_path: Path to Excel workbook file

    Returns:
        Filename stem (without extension) as workbook ID
    """
    from pathlib import Path

    return Path(file_path).stem


def generate_table_id(
    tag_type: str,
    logical_name: str | None,
    workbook_id: str,
    sheet_name: str,
    tag_position: str,
    veda_tag_text: str | None = None,
) -> str:
    """Generate stable table_id from VEDA table metadata.

    ID format:
    - With logical name: {workbook_id}__{sheet_name}__{tag_type}__{logical_name}
    - Without logical name: {workbook_id}__{sheet_name}__{tag_type}

    Args:
        tag_type: VEDA tag type (e.g., 'fi_t', 'fi_process')
        logical_name: Optional logical table name
        workbook_id: Workbook identifier
        sheet_name: Sheet containing the table
        tag_position: Cell position of VEDA tag (e.g., 'B5')
        veda_tag_text: Full VEDA tag text (for hash fallback)

    Returns:
        Deterministic table identifier
    """
    tag_upper = tag_type.upper()

    # Normalize sheet name and logical name for filesystem safety
    sheet_safe = _normalize_name(sheet_name)

    if logical_name:
        logical_safe = _normalize_name(logical_name)
        return f"{workbook_id}__{sheet_safe}__{tag_upper}__{logical_safe}"
    else:
        return f"{workbook_id}__{sheet_safe}__{tag_upper}"


def _normalize_name(name: str) -> str:
    """Normalize logical name to stable, filesystem-safe identifier.

    Rules:
    - Convert to lowercase
    - Strip leading/trailing whitespace
    - Collapse multiple spaces to single space
    - Replace spaces with underscores
    - Replace special characters with underscores

    Args:
        name: Raw logical name

    Returns:
        Normalized name (lowercase, alphanumeric + underscore only)
    """
    # Strip and convert to lowercase
    name = name.strip().lower()

    # Collapse multiple whitespace to single space
    name = re.sub(r"\s+", " ", name)

    # Replace spaces with underscores
    name = name.replace(" ", "_")

    # Replace special characters (except alphanumeric and underscore) with underscore
    name = re.sub(r"[^a-z0-9_]", "_", name)

    return name
