"""Column canonicalizer for VEDA tables - ordering and filling logic."""

import logging

import pandas as pd

from austimes_tables.veda import VedaSchema

logger = logging.getLogger(__name__)


def canonicalize_columns(
    df: pd.DataFrame, schema: VedaSchema, tag_type: str, keep_unknown: bool = True
) -> pd.DataFrame:
    """Reorder and fill DataFrame columns to match VEDA schema canonical order.

    Args:
        df: Input DataFrame with VEDA table data
        schema: VedaSchema instance for field definitions
        tag_type: VEDA tag name (e.g., 'fi_t', 'fi_process')
        keep_unknown: If True, keep unknown columns at end; if False, drop them

    Returns:
        DataFrame with columns in canonical schema order, missing columns added,
        and optionally unknown columns at the end or dropped

    Example:
        >>> schema = VedaSchema()
        >>> df = pd.DataFrame({'Year': [2020], 'Region': ['AUS'], 'Pset_PN': ['...']})
        >>> canonical_df = canonicalize_columns(df, schema, 'fi_t')
    """
    if df.empty:
        return df.copy()

    valid_fields = schema.get_valid_fields(tag_type)
    if not valid_fields:
        logger.warning(f"No valid fields found for tag_type '{tag_type}'")
        return df.copy()

    current_columns = list(df.columns)

    df_col_to_canonical: dict[str, str] = {}
    for col in current_columns:
        canonical = schema.get_canonical_name(tag_type, col)
        if canonical:
            df_col_to_canonical[col] = canonical

    canonical_to_df_col: dict[str, str] = {
        canonical: df_col for df_col, canonical in df_col_to_canonical.items()
    }

    canonical_columns: list[str] = []
    columns_to_add: list[str] = []

    for schema_field in valid_fields:
        schema_field_lower = schema_field.lower()

        if schema_field_lower in canonical_to_df_col:
            canonical_columns.append(canonical_to_df_col[schema_field_lower])
        else:
            field_metadata = schema.get_field_metadata(tag_type, schema_field)
            is_required = field_metadata.get("required", False) if field_metadata else False

            if not is_required:
                canonical_columns.append(schema_field)
                columns_to_add.append(schema_field)
                logger.debug(
                    f"Adding missing optional column '{schema_field}' for tag '{tag_type}'"
                )
            else:
                logger.warning(
                    f"Required column '{schema_field}' missing from DataFrame for tag '{tag_type}'"
                )
                canonical_columns.append(schema_field)
                columns_to_add.append(schema_field)

    recognized_df_cols = set(canonical_to_df_col.values())
    unknown_columns = [col for col in current_columns if col not in recognized_df_cols]

    if unknown_columns:
        if keep_unknown:
            logger.debug(
                f"Keeping {len(unknown_columns)} unknown columns at end: {unknown_columns}"
            )
            canonical_columns.extend(unknown_columns)
        else:
            logger.warning(f"Dropping {len(unknown_columns)} unknown columns: {unknown_columns}")

    result_df = df.copy()

    for col in columns_to_add:
        result_df[col] = None

    result_df = result_df[canonical_columns]

    return result_df
