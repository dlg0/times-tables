"""Validate command implementation - checks shadow tables against schema."""

import logging
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from times_tables.index import TablesIndexIO
from times_tables.veda import VedaSchema

logger = logging.getLogger(__name__)


def validate_deck(deck_root: str) -> int:
    """Validate shadow tables against VEDA schema.

    Args:
        deck_root: Path to VEDA deck root directory

    Returns:
        0 if all tables valid, 1 if validation errors found

    Validation checks:
        - tables_index.json exists and is valid
        - All CSV files referenced in index exist
        - Required columns present (from schema)
        - Primary key columns exist
        - No NULL values in primary key columns
        - No duplicate primary keys
        - All columns known to schema (warn on unknown)
    """
    deck_path = Path(deck_root).resolve()
    shadow_dir = deck_path / "shadow"
    meta_dir = shadow_dir / "meta"
    index_path = meta_dir / "tables_index.json"

    # Check index exists
    if not index_path.exists():
        print(f"❌ tables_index.json not found: {index_path}")
        print("   Run 'times-tables extract' first")
        return 1

    # Load index
    try:
        index = TablesIndexIO.read(str(index_path))
    except Exception as e:
        print(f"❌ Failed to read tables_index.json: {e}")
        return 1

    if not index.tables:
        print("⚠️  No tables found in index")
        return 0

    # Load schema
    schema = VedaSchema()

    # Validate each table
    all_errors: List[str] = []
    all_warnings: List[str] = []
    tables_checked = 0

    for composite_key, table_meta in index.tables.items():
        tables_checked += 1

        # Check CSV file exists - csv_path is relative to shadow dir
        csv_path = shadow_dir / table_meta.csv_path
        if not csv_path.exists():
            all_errors.append(f"{composite_key}: CSV file not found: {table_meta.csv_path}")
            continue

        # Read CSV
        try:
            df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError:
            # Empty CSV file is valid (0 rows, 0 columns)
            if table_meta.row_count == 0 and len(table_meta.columns) == 0:
                continue
            else:
                all_errors.append(
                    f"{composite_key}: CSV file is empty but index expects "
                    f"{table_meta.row_count} rows and {len(table_meta.columns)} columns"
                )
                continue
        except Exception as e:
            all_errors.append(f"{composite_key}: Failed to read CSV: {e}")
            continue

        # Validate table
        errors, warnings = _validate_table(
            table_meta.tag_type,
            df,
            table_meta.columns,
            table_meta.primary_keys,
            schema,
            composite_key,
        )

        all_errors.extend(errors)
        all_warnings.extend(warnings)

    # Print results
    if all_warnings:
        for warning in all_warnings:
            print(f"⚠️  {warning}")

    if all_errors:
        print(f"\n❌ Validation failed with {len(all_errors)} error(s):")
        for error in all_errors:
            print(f"  - {error}")
        return 1
    else:
        print(f"✓ All {tables_checked} table(s) valid")
        return 0


def _validate_table(
    tag_type: str,
    df: pd.DataFrame,
    expected_columns: List[str],
    primary_keys: List[str],
    schema: VedaSchema,
    table_id: str,
) -> Tuple[List[str], List[str]]:
    """Validate a single table against schema.

    Args:
        tag_type: VEDA tag type (e.g., 'fi_t')
        df: DataFrame loaded from CSV
        expected_columns: Expected column names from index
        primary_keys: Primary key column names from index
        schema: VedaSchema instance
        table_id: Composite table ID for error messages

    Returns:
        Tuple of (errors, warnings) as lists of strings
    """
    errors = []
    warnings = []

    actual_columns = list(df.columns)

    # Check columns match index
    if actual_columns != expected_columns:
        errors.append(
            f"{table_id}: Column mismatch - CSV has {actual_columns}, "
            f"index expects {expected_columns}"
        )
        # Continue validation with actual columns

    # Get schema definition
    tag_def = schema.get_tag(tag_type)
    if tag_def is None:
        warnings.append(f"{table_id}: Unknown tag type '{tag_type}' - skipping schema validation")
        # Continue with basic validation even without schema
    else:
        # Check for unknown columns
        valid_fields = schema.get_valid_fields(tag_type)
        valid_fields_lower = [f.lower() for f in valid_fields]

        for col in actual_columns:
            canonical = schema.get_canonical_name(tag_type, col)
            if canonical is None and col.lower() not in valid_fields_lower:
                warnings.append(f"{table_id}: Unknown column '{col}' not in schema for {tag_type}")

    # Validate primary keys exist
    for pk in primary_keys:
        if pk not in actual_columns:
            errors.append(f"{table_id}: Primary key column '{pk}' not found in CSV")

    # If PK columns exist, check for NULLs and duplicates
    if all(pk in actual_columns for pk in primary_keys):
        # Check for NULL values in PK columns
        for pk in primary_keys:
            null_mask = df[pk].isna() | (df[pk] == "")
            if null_mask.any():
                null_rows = df.index[null_mask].tolist()
                # CSV rows are 1-indexed with header at row 1, so data starts at row 2
                csv_rows = [r + 2 for r in null_rows]
                errors.append(
                    f"{table_id}: NULL values in primary key column '{pk}' "
                    f"at CSV rows: {csv_rows[:5]}"
                    + (f" ... (+{len(csv_rows) - 5} more)" if len(csv_rows) > 5 else "")
                )

        # Check for duplicate primary keys
        if primary_keys:
            pk_subset = df[primary_keys]
            duplicates = pk_subset[pk_subset.duplicated(keep=False)]

            if not duplicates.empty:
                dup_rows = duplicates.index.tolist()
                csv_rows = [r + 2 for r in dup_rows]
                errors.append(
                    f"{table_id}: Duplicate primary keys found at CSV rows: "
                    f"{csv_rows[:5]}"
                    + (f" ... (+{len(csv_rows) - 5} more)" if len(csv_rows) > 5 else "")
                )

    return errors, warnings
