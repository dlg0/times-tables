"""Deterministic row sorting for VEDA tables."""

import pandas as pd


def sort_by_primary_keys(df: pd.DataFrame, primary_keys: list[str]) -> pd.DataFrame:
    """Sort DataFrame by primary key columns in deterministic lexicographic order.

    Args:
        df: DataFrame to sort
        primary_keys: List of column names to sort by (in order)

    Returns:
        New sorted DataFrame (does not modify original)

    Sorting semantics:
        - Lexicographic tuple ordering
        - Case-sensitive string comparison
        - NaN/None values sort last
        - Stable sort for determinism
        - PK columns normalized to strings for consistent ordering
    """
    if df.empty:
        return df.copy()

    if not primary_keys:
        return df.copy()

    df_sorted = df.copy()

    # Filter primary keys to only those present in the DataFrame
    valid_pks = [pk for pk in primary_keys if pk in df_sorted.columns]

    if not valid_pks:
        # No valid primary keys found, return unsorted
        return df_sorted

    # Log warning if some PKs are missing
    missing_pks = set(primary_keys) - set(valid_pks)
    if missing_pks:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Primary keys {missing_pks} not found in DataFrame columns, using {valid_pks}"
        )

    for pk in valid_pks:
        df_sorted[pk] = df_sorted[pk].astype(str).replace("nan", pd.NA).replace("<NA>", pd.NA)

    df_sorted = df_sorted.sort_values(by=valid_pks, kind="stable", na_position="last")

    for pk in valid_pks:
        df_sorted[pk] = df_sorted[pk].fillna("")

    return df_sorted
