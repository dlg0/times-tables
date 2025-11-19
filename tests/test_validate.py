"""Unit tests for validate command."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from times_tables.commands.validate import validate_deck
from times_tables.csvio import write_deterministic_csv
from times_tables.index import TablesIndexIO
from times_tables.models import TableMeta, TablesIndex, WorkbookMeta


@pytest.fixture
def temp_deck():
    """Create temporary deck directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        deck_path = Path(tmpdir)
        shadow_dir = deck_path / "shadow"
        meta_dir = shadow_dir / "meta"
        tables_dir = shadow_dir / "tables"

        meta_dir.mkdir(parents=True)
        tables_dir.mkdir(parents=True)

        yield deck_path


def _create_test_index(deck_path: Path, tables_meta: list[TableMeta]) -> TablesIndex:
    """Helper to create tables_index.json with given table metadata."""
    index = TablesIndex.create_empty("times-tables/test")

    # Add a dummy workbook
    workbook = WorkbookMeta(workbook_id="test1234", source_path="test.xlsx", hash="sha256:dummy")
    index.add_workbook(workbook)

    # Add tables
    for table_meta in tables_meta:
        index.add_table(table_meta)

    # Write index
    index_path = deck_path / "shadow" / "meta" / "tables_index.json"
    TablesIndexIO.write(index, str(index_path))

    return index


def test_validate_missing_index(temp_deck):
    """Test validation fails when tables_index.json doesn't exist."""
    result = validate_deck(str(temp_deck))
    assert result == 1


def test_validate_empty_deck(temp_deck):
    """Test validation succeeds for empty deck."""
    _create_test_index(temp_deck, [])
    result = validate_deck(str(temp_deck))
    assert result == 0


def test_validate_valid_table(temp_deck):
    """Test validation passes for valid table."""
    # Create valid table
    df = pd.DataFrame(
        {
            "Region": ["AUS", "NZ"],
            "Process": ["COAL", "GAS"],
            "Year": ["2020", "2025"],
            "Value": ["100.5", "75.2"],
        }
    )

    csv_path = temp_deck / "shadow" / "tables" / "test1234" / "table1.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    sha256 = write_deterministic_csv(
        df,
        str(csv_path),
        primary_keys=["Region", "Process", "Year"],
        column_order=["Region", "Process", "Year", "Value"],
    )

    # Create index
    table_meta = TableMeta(
        table_id="table1",
        workbook_id="test1234",
        sheet_name="Sheet1",
        tag="~FI_T",
        tag_type="fi_t",
        logical_name=None,
        tag_position="B2",
        columns=["Region", "Process", "Year", "Value"],
        primary_keys=["Region", "Process", "Year"],
        row_count=2,
        csv_path="tables/test1234/table1.csv",
        csv_sha256=sha256,
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    _create_test_index(temp_deck, [table_meta])

    result = validate_deck(str(temp_deck))
    assert result == 0


def test_validate_missing_csv(temp_deck):
    """Test validation fails when CSV file doesn't exist."""
    table_meta = TableMeta(
        table_id="table1",
        workbook_id="test1234",
        sheet_name="Sheet1",
        tag="~FI_T",
        tag_type="fi_t",
        logical_name=None,
        tag_position="B2",
        columns=["Region", "Process"],
        primary_keys=["Region"],
        row_count=1,
        csv_path="tables/test1234/nonexistent.csv",
        csv_sha256="dummy",
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    _create_test_index(temp_deck, [table_meta])

    result = validate_deck(str(temp_deck))
    assert result == 1


def test_validate_null_in_primary_key(temp_deck):
    """Test validation fails when primary key has NULL values."""
    # Create table with NULL in PK
    df = pd.DataFrame(
        {
            "Region": ["AUS", ""],  # Empty string = NULL
            "Process": ["COAL", "GAS"],
            "Value": ["100", "75"],
        }
    )

    csv_path = temp_deck / "shadow" / "tables" / "test1234" / "table1.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    sha256 = write_deterministic_csv(
        df,
        str(csv_path),
        primary_keys=["Region", "Process"],
        column_order=["Region", "Process", "Value"],
    )

    table_meta = TableMeta(
        table_id="table1",
        workbook_id="test1234",
        sheet_name="Sheet1",
        tag="~FI_T",
        tag_type="fi_t",
        logical_name=None,
        tag_position="B2",
        columns=["Region", "Process", "Value"],
        primary_keys=["Region", "Process"],
        row_count=2,
        csv_path="tables/test1234/table1.csv",
        csv_sha256=sha256,
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    _create_test_index(temp_deck, [table_meta])

    result = validate_deck(str(temp_deck))
    assert result == 1


def test_validate_duplicate_primary_key(temp_deck):
    """Test validation fails with duplicate primary keys."""
    # Create table with duplicate PKs
    df = pd.DataFrame(
        {
            "Region": ["AUS", "AUS"],  # Duplicate PK
            "Process": ["COAL", "COAL"],  # Duplicate PK
            "Value": ["100", "200"],
        }
    )

    csv_path = temp_deck / "shadow" / "tables" / "test1234" / "table1.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    sha256 = write_deterministic_csv(
        df,
        str(csv_path),
        primary_keys=["Region", "Process"],
        column_order=["Region", "Process", "Value"],
    )

    table_meta = TableMeta(
        table_id="table1",
        workbook_id="test1234",
        sheet_name="Sheet1",
        tag="~FI_T",
        tag_type="fi_t",
        logical_name=None,
        tag_position="B2",
        columns=["Region", "Process", "Value"],
        primary_keys=["Region", "Process"],
        row_count=2,
        csv_path="tables/test1234/table1.csv",
        csv_sha256=sha256,
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    _create_test_index(temp_deck, [table_meta])

    result = validate_deck(str(temp_deck))
    assert result == 1


def test_validate_missing_pk_column(temp_deck):
    """Test validation fails when primary key column is missing."""
    df = pd.DataFrame(
        {
            "Region": ["AUS"],
            "Value": ["100"],
            # Process column missing but declared in PK
        }
    )

    csv_path = temp_deck / "shadow" / "tables" / "test1234" / "table1.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    sha256 = write_deterministic_csv(
        df, str(csv_path), primary_keys=["Region"], column_order=["Region", "Value"]
    )

    table_meta = TableMeta(
        table_id="table1",
        workbook_id="test1234",
        sheet_name="Sheet1",
        tag="~FI_T",
        tag_type="fi_t",
        logical_name=None,
        tag_position="B2",
        columns=["Region", "Value"],
        primary_keys=["Region", "Process"],  # Process declared but missing
        row_count=1,
        csv_path="tables/test1234/table1.csv",
        csv_sha256=sha256,
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    _create_test_index(temp_deck, [table_meta])

    result = validate_deck(str(temp_deck))
    assert result == 1


def test_validate_column_mismatch(temp_deck):
    """Test validation fails when CSV columns don't match index."""
    df = pd.DataFrame(
        {
            "Region": ["AUS"],
            "Process": ["COAL"],
            "ExtraColumn": ["unexpected"],  # Not in index
        }
    )

    csv_path = temp_deck / "shadow" / "tables" / "test1234" / "table1.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    sha256 = write_deterministic_csv(
        df,
        str(csv_path),
        primary_keys=["Region"],
        column_order=["Region", "Process", "ExtraColumn"],
    )

    table_meta = TableMeta(
        table_id="table1",
        workbook_id="test1234",
        sheet_name="Sheet1",
        tag="~FI_T",
        tag_type="fi_t",
        logical_name=None,
        tag_position="B2",
        columns=["Region", "Process"],  # No ExtraColumn
        primary_keys=["Region"],
        row_count=1,
        csv_path="tables/test1234/table1.csv",
        csv_sha256=sha256,
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    _create_test_index(temp_deck, [table_meta])

    result = validate_deck(str(temp_deck))
    assert result == 1


def test_validate_multiple_tables_mixed(temp_deck):
    """Test validation with multiple tables, some valid, some invalid."""
    # Valid table 1
    df1 = pd.DataFrame({"Region": ["AUS"], "Process": ["COAL"], "Value": ["100"]})
    csv1_path = temp_deck / "shadow" / "tables" / "test1234" / "table1.csv"
    csv1_path.parent.mkdir(parents=True, exist_ok=True)
    sha1 = write_deterministic_csv(
        df1,
        str(csv1_path),
        primary_keys=["Region", "Process"],
        column_order=["Region", "Process", "Value"],
    )

    # Invalid table 2 (duplicate PK)
    df2 = pd.DataFrame({"Region": ["NZ", "NZ"], "Process": ["GAS", "GAS"], "Value": ["50", "60"]})
    csv2_path = temp_deck / "shadow" / "tables" / "test1234" / "table2.csv"
    csv2_path.parent.mkdir(parents=True, exist_ok=True)
    sha2 = write_deterministic_csv(
        df2,
        str(csv2_path),
        primary_keys=["Region", "Process"],
        column_order=["Region", "Process", "Value"],
    )

    table1 = TableMeta(
        table_id="table1",
        workbook_id="test1234",
        sheet_name="Sheet1",
        tag="~FI_T",
        tag_type="fi_t",
        logical_name=None,
        tag_position="B2",
        columns=["Region", "Process", "Value"],
        primary_keys=["Region", "Process"],
        row_count=1,
        csv_path="tables/test1234/table1.csv",
        csv_sha256=sha1,
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    table2 = TableMeta(
        table_id="table2",
        workbook_id="test1234",
        sheet_name="Sheet2",
        tag="~FI_T",
        tag_type="fi_t",
        logical_name=None,
        tag_position="B5",
        columns=["Region", "Process", "Value"],
        primary_keys=["Region", "Process"],
        row_count=2,
        csv_path="tables/test1234/table2.csv",
        csv_sha256=sha2,
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    _create_test_index(temp_deck, [table1, table2])

    result = validate_deck(str(temp_deck))
    assert result == 1  # Should fail due to table2
