"""Format command implementation - re-canonicalizes existing shadow CSVs."""

import logging
from pathlib import Path

import pandas as pd
from rich.console import Console

from times_tables.csvio import write_deterministic_csv
from times_tables.index import TablesIndexIO
from times_tables.veda import VedaSchema

logger = logging.getLogger(__name__)
console = Console()


def format_deck(deck_root: str) -> int:
    """Re-canonicalize existing shadow CSVs with deterministic formatting.

    This command:
    1. Reads tables_index.json from shadow/meta/
    2. Loads VedaSchema
    3. For each table in index:
       - Reads CSV to DataFrame
       - Sorts by primary keys
       - Writes back deterministically
       - Updates CSV hash in index
    4. Writes updated tables_index.json

    Args:
        deck_root: Path to VEDA deck root directory

    Returns:
        0 on success, 1 on error

    Raises:
        FileNotFoundError: If shadow directory or required files don't exist
        ValueError: If formatting fails
    """
    deck_path = Path(deck_root).resolve()
    if not deck_path.exists():
        console.print(f"[red]Error:[/red] Deck root not found: {deck_root}")
        return 1

    if not deck_path.is_dir():
        console.print(f"[red]Error:[/red] Deck root must be a directory: {deck_root}")
        return 1

    # Locate shadow directory
    shadow_dir = deck_path / "shadow"
    if not shadow_dir.exists():
        console.print(f"[red]Error:[/red] Shadow directory not found: {shadow_dir}")
        console.print("Run 'extract' command first to create shadow tables")
        return 1

    meta_dir = shadow_dir / "meta"
    index_path = meta_dir / "tables_index.json"

    if not index_path.exists():
        console.print(f"[red]Error:[/red] Index file not found: {index_path}")
        console.print("Run 'extract' command first to create tables index")
        return 1

    # Read tables index
    try:
        index = TablesIndexIO.read(str(index_path))
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read tables index: {e}")
        return 1

    # Initialize schema
    schema = VedaSchema()

    console.print(f"[cyan]Formatting[/cyan] {len(index.tables)} tables...")

    # Track statistics
    formatted_count = 0
    error_count = 0

    # Format each table
    for composite_key, table_meta in index.tables.items():
        table_id = table_meta.table_id
        csv_path = shadow_dir / table_meta.csv_path

        # Check if CSV file exists
        if not csv_path.exists():
            console.print(f"  [yellow]⚠[/yellow] CSV file not found: {table_meta.csv_path}")
            error_count += 1
            continue

        try:
            # Check if file is empty or has no content
            csv_size = csv_path.stat().st_size
            if csv_size <= 1:  # Empty or just newline
                logger.debug(f"  Skipping empty CSV {table_id}")
                formatted_count += 1
                continue

            # Read CSV
            df = pd.read_csv(csv_path, encoding="utf-8", dtype=str, keep_default_na=False)

            # Skip empty tables (no data rows)
            if df.empty:
                logger.debug(f"  Skipping empty table {table_id}")
                formatted_count += 1
                continue

            # Get primary keys from table metadata
            primary_keys = table_meta.primary_keys
            if not primary_keys:
                # Fallback to schema
                primary_keys = schema.get_primary_keys(table_meta.tag_type)
                if not primary_keys:
                    logger.warning(f"  No primary keys for {table_id}, using all columns")
                    primary_keys = list(df.columns)

            # Get column order from table metadata
            column_order = table_meta.columns

            # Verify all columns exist in DataFrame
            missing_cols = [col for col in column_order if col not in df.columns]
            if missing_cols:
                console.print(
                    f"  [yellow]⚠[/yellow] Columns in index but not in CSV "
                    f"for {table_id}: {missing_cols}"
                )
                # Use actual DataFrame columns
                column_order = list(df.columns)

            # Write back with deterministic formatting
            new_csv_sha256 = write_deterministic_csv(
                df=df, path=str(csv_path), primary_keys=primary_keys, column_order=column_order
            )

            # Update hash in index
            old_hash = table_meta.csv_sha256
            table_meta.csv_sha256 = new_csv_sha256

            # Log if hash changed
            if old_hash != new_csv_sha256:
                logger.debug(f"  Updated hash for {table_id}")

            console.print(f"  [green]✓[/green] Formatted {table_id}")
            formatted_count += 1

        except Exception as e:
            console.print(f"  [red]✗[/red] Failed to format {table_id}: {e}")
            error_count += 1
            continue

    # Write updated index
    try:
        TablesIndexIO.write(index, str(index_path))
        console.print(f"[green]✓[/green] Formatted {formatted_count} tables")

        if error_count > 0:
            console.print(f"[yellow]![/yellow] {error_count} tables had errors")
            return 1

        return 0

    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to write updated index: {e}")
        return 1
