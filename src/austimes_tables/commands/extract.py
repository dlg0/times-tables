"""Extract command implementation - orchestrates full extraction workflow."""

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from austimes_tables import extract, ids, scanner
from austimes_tables.csvio import write_deterministic_csv
from austimes_tables.index import TablesIndexIO
from austimes_tables.models import TableMeta, TablesIndex, WorkbookMeta
from austimes_tables.veda import VedaSchema

logger = logging.getLogger(__name__)


def extract_deck(deck_root: str, output_dir: str = "shadow", verbose: bool = False) -> TablesIndex:
    """Extract all VEDA tables from a deck to shadow CSV files.

    Args:
        deck_root: Path to VEDA deck root directory
        output_dir: Output directory name (default: 'shadow')
        verbose: Enable verbose logging

    Returns:
        TablesIndex containing metadata for all extracted tables

    Raises:
        FileNotFoundError: If deck_root doesn't exist
        ValueError: If extraction fails for any table
    """
    deck_path = Path(deck_root).resolve()
    if not deck_path.exists():
        raise FileNotFoundError(f"Deck root not found: {deck_root}")

    if not deck_path.is_dir():
        raise ValueError(f"Deck root must be a directory: {deck_root}")

    # Determine shadow directory (can be absolute or relative to deck_root)
    if Path(output_dir).is_absolute():
        shadow_dir = Path(output_dir)
    else:
        shadow_dir = deck_path / output_dir

    tables_dir = shadow_dir / "tables"
    meta_dir = shadow_dir / "meta"

    # Create directory structure
    tables_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Initialize index
    index = TablesIndexIO.create_empty(generator="austimes-tables/0.1.0")

    # Initialize schema
    schema = VedaSchema()

    # Find all Excel workbooks in deck_root and SupplXLS/
    workbook_paths = []
    workbook_paths.extend(deck_path.glob("*.xlsx"))
    workbook_paths.extend(deck_path.glob("*.xls"))

    suppl_dir = deck_path / "SupplXLS"
    if suppl_dir.exists():
        workbook_paths.extend(suppl_dir.glob("*.xlsx"))
        workbook_paths.extend(suppl_dir.glob("*.xls"))

    # Process each workbook
    for workbook_path in sorted(workbook_paths):
        logger.info(f"Scanning {workbook_path.name}...")

        # Generate workbook_id (hash of file content)
        workbook_id = ids.generate_workbook_id(str(workbook_path))

        # Compute workbook hash (SHA256)
        with open(workbook_path, "rb") as f:
            workbook_hash = hashlib.sha256(f.read()).hexdigest()

        # Compute relative path from deck_root
        try:
            relative_path = workbook_path.relative_to(deck_path)
        except ValueError:
            # If not relative to deck_path, use absolute
            relative_path = workbook_path

        # Add workbook to index
        workbook_meta = WorkbookMeta(
            workbook_id=workbook_id, source_path=str(relative_path), hash=f"sha256:{workbook_hash}"
        )
        index.add_workbook(workbook_meta)

        # Scan for tables
        try:
            tables = scanner.scan_workbook(str(workbook_path))
        except Exception as e:
            logger.warning(f"  Failed to scan {workbook_path.name}: {e}")
            continue

        logger.info(f"  Found {len(tables)} tables")

        # Process each table
        for table_info in tables:
            # Generate table_id
            tag_type = table_info["tag_type"]
            logical_name = table_info.get("logical_name")
            sheet_name = table_info["sheet_name"]
            tag_row = table_info["tag_row"]
            tag_col = table_info["tag_col"]
            tag_position = f"{_col_to_letter(tag_col)}{tag_row}"
            veda_tag = table_info["tag"]

            table_id = ids.generate_table_id(
                tag_type=tag_type,
                logical_name=logical_name,
                workbook_id=workbook_id,
                sheet_name=sheet_name,
                tag_position=tag_position,
                veda_tag_text=veda_tag,
            )

            # Extract table to DataFrame
            try:
                df = extract.extract_table(
                    workbook_path=str(workbook_path), table_meta=table_info, schema=schema
                )
            except Exception as e:
                logger.warning(f"  Failed to extract {table_id}: {e}")
                continue

            # Skip canonicalize for now - just use extracted columns as-is
            # TODO: Implement proper column canonicalization that preserves case
            # df = canonicalize_columns(
            #     df=df,
            #     schema=schema,
            #     tag_type=tag_type,
            #     keep_unknown=True
            # )

            # Get primary keys from schema
            primary_keys = schema.get_primary_keys(tag_type)
            if not primary_keys:
                # Fallback: use all columns as PK
                logger.debug(f"  No primary key for {tag_type}, using all columns")
                primary_keys = list(df.columns)

            # Create workbook subdirectory
            workbook_dir = tables_dir / workbook_id
            workbook_dir.mkdir(exist_ok=True)

            # Write CSV
            csv_path = workbook_dir / f"{table_id}.csv"
            csv_sha256 = write_deterministic_csv(
                df=df, path=str(csv_path), primary_keys=primary_keys, column_order=list(df.columns)
            )

            # Compute relative path for csv_path (relative to shadow_dir)
            csv_relative_path = csv_path.relative_to(shadow_dir)

            row_count = len(df)
            logger.info(f"  Extracted {table_id} ({row_count} rows)")

            # Add table to index
            table_meta = TableMeta(
                table_id=table_id,
                workbook_id=workbook_id,
                sheet_name=sheet_name,
                tag=veda_tag,
                tag_type=tag_type,
                logical_name=logical_name,
                tag_position=tag_position,
                columns=list(df.columns),
                primary_keys=primary_keys,
                row_count=row_count,
                csv_path=str(csv_relative_path),
                csv_sha256=csv_sha256,
                extracted_at=datetime.utcnow().isoformat() + "Z",
                schema_version="veda-tags-2024",
            )
            index.add_table(table_meta)

    # Write tables_index.json
    index_path = meta_dir / "tables_index.json"
    TablesIndexIO.write(index, str(index_path))
    logger.info(f"Wrote {index_path.relative_to(deck_path)}")

    return index


def _col_to_letter(col: int) -> str:
    """Convert 1-indexed column number to Excel letter (1→A, 27→AA, etc.)."""
    result = []
    col -= 1  # Make 0-indexed
    while col >= 0:
        result.append(chr(col % 26 + ord("A")))
        col = col // 26 - 1
    return "".join(reversed(result))
