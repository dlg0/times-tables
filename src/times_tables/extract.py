"""Extract VEDA tables to pandas DataFrames.

Extracts tables from Excel workbooks, normalizes column names and values,
and returns pandas DataFrames ready for CSV export.
"""

import logging
from typing import Any

import pandas as pd
from openpyxl import Workbook

from times_tables import excel
from times_tables.veda import VedaSchema

logger = logging.getLogger(__name__)


def extract_table(
    workbook: Workbook, table_meta: dict[str, Any], schema: VedaSchema
) -> pd.DataFrame:
    """Extract a VEDA table to a pandas DataFrame.

    Args:
        workbook: openpyxl Workbook object
        table_meta: Table metadata from scanner.scan_workbook()
        schema: VedaSchema instance for column name normalization

    Returns:
        pandas DataFrame with normalized column names and string values

    Raises:
        ValueError: If sheet not found or columns don't match schema
    """

    # Get sheet by name
    sheet_name = table_meta["sheet_name"]
    if sheet_name not in workbook.sheetnames:
        raise ValueError(
            f"Sheet '{sheet_name}' not found in workbook. Available sheets: {workbook.sheetnames}"
        )

    sheet = workbook[sheet_name]

    # Read table range using excel utility
    tag_row = table_meta["tag_row"]
    tag_col = table_meta["tag_col"]
    headers, data_rows = excel.read_table_range(sheet, tag_row, tag_col)

    # Build DataFrame from headers + rows
    if not headers:
        logger.warning(
            f"Table {table_meta['tag']} at {sheet_name}!{tag_row}:{tag_col} has no headers"
        )
        return pd.DataFrame()

    # Normalize column names (resolve aliases to canonical names)
    tag_type = table_meta["tag_type"]
    canonical_headers = []
    unknown_columns = []

    for header in headers:
        canonical = schema.get_canonical_name(tag_type, header)
        if canonical is not None:
            canonical_headers.append(canonical)
        else:
            # Keep original header if not found in schema
            canonical_headers.append(header)
            unknown_columns.append(header)

    # Warn about unknown columns
    if unknown_columns:
        logger.warning(
            f"Table {table_meta['tag']} has unknown columns not in schema: {unknown_columns}"
        )

    # Create DataFrame with normalized column names
    df = pd.DataFrame(data_rows, columns=canonical_headers)

    # Normalize values
    df = _normalize_values(df)

    return df


def _normalize_values(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataFrame values for deterministic CSV output.

    Args:
        df: Input DataFrame with mixed types

    Returns:
        DataFrame with normalized string values
    """
    result = df.copy()
    for col in result.columns:
        s = result[col]
        # Keep nulls as nulls
        mask = s.notna()
        # Convert only non-nulls to str and strip
        s2 = s.where(~mask, s.astype(str).str.strip())
        # Empty strings -> None
        s2 = s2.mask(s2 == "", None)
        result[col] = s2
    return result
