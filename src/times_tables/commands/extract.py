"""Extract command implementation - orchestrates full extraction workflow."""

import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from times_tables import excel, extract, ids, scanner
from times_tables.csvio import write_deterministic_csv
from times_tables.index import TablesIndexIO
from times_tables.models import TableMeta, TablesIndex, WorkbookMeta
from times_tables.veda import VedaSchema

logger = logging.getLogger(__name__)
console = Console()


def extract_deck(
    deck_root: str,
    output_dir: str = "shadow",
    verbose: bool = False,
    files: list[str] | None = None,
) -> TablesIndex:
    """Extract all VEDA tables from a deck to shadow CSV files.

    Args:
        deck_root: Path to VEDA deck root directory
        output_dir: Output directory name (default: 'shadow')
        verbose: Enable verbose logging
        files: Optional list of specific workbook paths to extract (relative to deck_root)

    Returns:
        TablesIndex containing metadata for all extracted tables

    Raises:
        FileNotFoundError: If deck_root doesn't exist
        ValueError: If extraction fails for any table
    """
    start_time = time.time()

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
    index = TablesIndexIO.create_empty(generator="times-tables/0.1.0")

    # Track stats for summary
    workbook_stats = defaultdict(lambda: defaultdict(lambda: {"count": 0, "time": 0.0}))

    # Load previous index if exists (for incremental skip)
    index_path = meta_dir / "tables_index.json"
    prev_index = None
    if index_path.exists():
        try:
            prev_index = TablesIndexIO.read(str(index_path))
        except Exception as e:
            logger.warning(f"Failed to load previous index: {e}")

    # Build lookup for previous workbooks by (source_path, hash)
    prev_workbooks = {}
    if prev_index:
        for wb in prev_index.workbooks.values():
            key = (wb.source_path, wb.hash)
            prev_workbooks[key] = wb.workbook_id

    # Initialize schema
    schema = VedaSchema()

    # Find all Excel workbooks following VEDA naming conventions
    workbook_paths = []

    if files:
        # Use provided file list
        for f in files:
            path = deck_path / f
            if path.exists() and path.suffix.lower() in (".xlsx", ".xls"):
                workbook_paths.append(path)
            elif verbose:
                console.print(f"[dim]Skipping {f} (not found or not Excel)[/dim]")
    else:
        # Auto-discover files
        # Root directory: all .xlsx/.xls files
        workbook_paths.extend(deck_path.glob("*.xlsx"))
        workbook_paths.extend(deck_path.glob("*.xls"))

        # SuppXLS/: files prefixed with "Scen_"
        suppxls_dir = deck_path / "SuppXLS"
        if suppxls_dir.exists():
            workbook_paths.extend(suppxls_dir.glob("Scen_*.xlsx"))
            workbook_paths.extend(suppxls_dir.glob("Scen_*.xls"))

        # SuppXLS/Trades/: files prefixed with "Scen"
        trades_dir = deck_path / "SuppXLS" / "Trades"
        if trades_dir.exists():
            workbook_paths.extend(trades_dir.glob("Scen*.xlsx"))
            workbook_paths.extend(trades_dir.glob("Scen*.xls"))

        # SubRES_Tmpl/: files prefixed with "SubRES_"
        subres_dir = deck_path / "SubRES_Tmpl"
        if subres_dir.exists():
            workbook_paths.extend(subres_dir.glob("SubRES_*.xlsx"))
            workbook_paths.extend(subres_dir.glob("SubRES_*.xls"))

    # Process each workbook
    for workbook_path in sorted(workbook_paths):
        workbook_start_time = time.time()

        # Compute relative path from deck_root
        try:
            relative_path = workbook_path.relative_to(deck_path)
        except ValueError:
            # If not relative to deck_path, use absolute
            relative_path = workbook_path

        # Compute workbook hash (SHA256) using chunked hashing
        workbook_hash = excel.hash_workbook(str(workbook_path))
        hash_key = f"sha256:{workbook_hash}"

        # Check if workbook is unchanged from previous run
        prev_key = (str(relative_path), hash_key)
        if prev_key in prev_workbooks:
            # Workbook unchanged - reuse previous metadata
            prev_workbook_id = prev_workbooks[prev_key]

            # Copy workbook metadata
            prev_wb = prev_index.workbooks.get(prev_workbook_id)
            if prev_wb:
                index.add_workbook(prev_wb)

                # Copy all table metadata for this workbook
                for table in prev_index.tables.values():
                    if table.workbook_id == prev_workbook_id:
                        # Verify CSV file still exists
                        csv_full_path = shadow_dir / table.csv_path
                        if csv_full_path.exists():
                            index.add_table(table)
                        else:
                            logger.warning(f"CSV missing for {table.table_id}, will re-extract")
                            break
                else:
                    # All tables verified, skip this workbook
                    console.print(f"[dim]⊙ Skipped {workbook_path.name} (unchanged)[/dim]")
                    continue

        console.print(f"[cyan]Scanning[/cyan] {workbook_path.name}...")

        # Generate workbook_id (hash of file content)
        workbook_id = ids.generate_workbook_id(str(workbook_path))

        # Add workbook to index
        workbook_meta = WorkbookMeta(
            workbook_id=workbook_id, source_path=str(relative_path), hash=hash_key
        )
        index.add_workbook(workbook_meta)

        # Load workbook once
        try:
            workbook = excel.load_workbook(str(workbook_path))
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Failed to load {workbook_path.name}: {e}")
            continue

        # Scan for tables
        try:
            tables = scanner.scan_workbook(workbook)
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Failed to scan {workbook_path.name}: {e}")
            continue

        console.print(f"  [dim]Found {len(tables)} tables[/dim]")

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
                df = extract.extract_table(workbook=workbook, table_meta=table_info, schema=schema)
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Failed to extract {table_id}: {e}")
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
            console.print(f"  [green]✓[/green] Extracted {table_id} [dim]({row_count} rows)[/dim]")

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

            # Track stats
            workbook_stats[workbook_path.name][sheet_name]["count"] += 1

        # Record workbook processing time
        workbook_time = time.time() - workbook_start_time
        for sheet_name in workbook_stats[workbook_path.name]:
            workbook_stats[workbook_path.name][sheet_name]["time"] = workbook_time

    # Write tables_index.json
    index_path = meta_dir / "tables_index.json"
    TablesIndexIO.write(index, str(index_path))
    console.print(f"[blue]Wrote[/blue] {index_path.relative_to(deck_path)}")

    # Print summary table
    total_time = time.time() - start_time
    _print_extraction_summary(workbook_stats, total_time)

    return index


def _print_extraction_summary(workbook_stats: dict, total_time: float) -> None:
    """Print a summary table of extraction statistics."""
    if not workbook_stats:
        return

    console.print()
    console.print("[bold]Extraction Summary[/bold]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("File", style="dim")
    table.add_column("Sheet")
    table.add_column("Tables", justify="right")
    table.add_column("Time (s)", justify="right")

    total_tables = 0
    for workbook_name in sorted(workbook_stats.keys()):
        sheets = workbook_stats[workbook_name]
        for sheet_name in sorted(sheets.keys()):
            count = sheets[sheet_name]["count"]
            wb_time = sheets[sheet_name]["time"]
            total_tables += count
            table.add_row(workbook_name, sheet_name, str(count), f"{wb_time:.2f}")

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {total_tables} tables in {total_time:.2f}s")
    console.print()


def _col_to_letter(col: int) -> str:
    """Convert 1-indexed column number to Excel letter (1→A, 27→AA, etc.)."""
    result = []
    col -= 1  # Make 0-indexed
    while col >= 0:
        result.append(chr(col % 26 + ord("A")))
        col = col // 26 - 1
    return "".join(reversed(result))
