"""Deterministic CSV I/O for git-friendly table exports."""

import csv
import hashlib

import pandas as pd

from .sorting import sort_by_primary_keys


def write_deterministic_csv(
    df: pd.DataFrame,
    path: str,
    primary_keys: list[str],
    column_order: list[str] | None = None,
) -> str:
    """
    Write a DataFrame to CSV with deterministic formatting for stable git diffs.

    Args:
        df: DataFrame to write
        path: Output file path
        primary_keys: Column names to sort by (lexicographic, case-sensitive)
        column_order: Explicit column order (default: df.columns order)

    Returns:
        SHA256 hash of the written file

    Determinism invariants:
        - UTF-8 encoding (no BOM)
        - LF newlines (\\n) on all platforms
        - csv.QUOTE_MINIMAL (only quote when necessary)
        - Rows sorted lexicographically by primary_keys tuple
        - Empty string for NULL values
    """
    # Sort by primary keys
    sorted_df = sort_by_primary_keys(df, primary_keys)

    # Reorder columns if specified
    if column_order is not None:
        sorted_df = sorted_df[column_order]

    # Write with deterministic settings
    sorted_df.to_csv(
        path,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
        na_rep="",
    )

    # Compute SHA256 hash
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
