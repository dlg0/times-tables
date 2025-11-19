"""Tests for format command."""

import hashlib
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from times_tables.commands.format import format_deck
from times_tables.index import TablesIndexIO
from times_tables.models import TableMeta, TablesIndex, WorkbookMeta


@pytest.fixture
def temp_deck():
    """Create a temporary deck with shadow tables for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        deck_path = Path(tmpdir) / "test_deck"
        deck_path.mkdir()

        shadow_dir = deck_path / "shadow"
        tables_dir = shadow_dir / "tables"
        meta_dir = shadow_dir / "meta"

        tables_dir.mkdir(parents=True)
        meta_dir.mkdir(parents=True)

        # Create sample workbook directory
        workbook_id = "abc12345"
        workbook_dir = tables_dir / workbook_id
        workbook_dir.mkdir()

        # Create sample CSV with explicitly unsorted data (reverse order)
        table_id = "fi_t_test"
        pd.DataFrame(
            {
                "Region": ["QLD", "NSW", "AUS"],  # Reverse alphabetical order
                "Year": ["2025", "2020", "2030"],
                "Value": ["300", "200", "100"],
            }
        )

        csv_path = workbook_dir / f"{table_id}.csv"

        # Write CSV without proper sorting to simulate unformatted state
        # Use explicit row order to ensure unsorted
        with open(csv_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("Region,Year,Value\n")
            f.write("QLD,2025,300\n")
            f.write("NSW,2020,200\n")
            f.write("AUS,2030,100\n")

        # Compute initial hash
        with open(csv_path, "rb") as f:
            initial_hash = hashlib.sha256(f.read()).hexdigest()

        # Create tables index
        index = TablesIndex.create_empty(generator="test/1.0.0")

        workbook_meta = WorkbookMeta(
            workbook_id=workbook_id, source_path="test.xlsx", hash="sha256:fakehash"
        )
        index.add_workbook(workbook_meta)

        table_meta = TableMeta(
            table_id=table_id,
            workbook_id=workbook_id,
            sheet_name="Sheet1",
            tag="~FI_T: Test",
            tag_type="fi_t",
            logical_name="Test",
            tag_position="A1",
            columns=["Region", "Year", "Value"],
            primary_keys=["Region", "Year"],
            row_count=3,
            csv_path=f"tables/{workbook_id}/{table_id}.csv",
            csv_sha256=initial_hash,
            extracted_at="2024-01-01T00:00:00Z",
            schema_version="veda-tags-2024",
        )
        index.add_table(table_meta)

        # Write index
        index_path = meta_dir / "tables_index.json"
        TablesIndexIO.write(index, str(index_path))

        yield deck_path


def test_format_deck_success(temp_deck, capsys):
    """Test successful formatting of shadow tables."""
    result = format_deck(str(temp_deck))

    assert result == 0
    captured = capsys.readouterr()
    assert "Formatting 1 tables" in captured.out
    assert "Formatted fi_t_test" in captured.out
    assert "Formatted 1 tables" in captured.out


def test_format_preserves_data(temp_deck):
    """Test that format preserves data content."""
    # Read original data
    csv_path = temp_deck / "shadow" / "tables" / "abc12345" / "fi_t_test.csv"
    original_df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    original_rows = set(tuple(row) for row in original_df.values)

    # Format
    result = format_deck(str(temp_deck))
    assert result == 0

    # Read formatted data
    formatted_df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    formatted_rows = set(tuple(row) for row in formatted_df.values)

    # Data should be identical (same rows)
    assert original_rows == formatted_rows
    assert len(original_df) == len(formatted_df)
    assert list(original_df.columns) == list(formatted_df.columns)


def test_format_updates_hash(temp_deck):
    """Test that format updates CSV hash in index."""
    # Read original index
    index_path = temp_deck / "shadow" / "meta" / "tables_index.json"
    original_index = TablesIndexIO.read(str(index_path))
    original_hash = list(original_index.tables.values())[0].csv_sha256

    # Format
    result = format_deck(str(temp_deck))
    assert result == 0

    # Read updated index
    updated_index = TablesIndexIO.read(str(index_path))
    updated_hash = list(updated_index.tables.values())[0].csv_sha256

    # Hash should be updated (because we're sorting by primary keys)
    # Original CSV was not sorted, so hash should change
    assert updated_hash != original_hash


def test_format_idempotent(temp_deck):
    """Test that format is idempotent (format twice → same result)."""
    # First format
    result1 = format_deck(str(temp_deck))
    assert result1 == 0

    # Read CSV and index after first format
    csv_path = temp_deck / "shadow" / "tables" / "abc12345" / "fi_t_test.csv"
    with open(csv_path, "rb") as f:
        csv_content1 = f.read()

    index_path = temp_deck / "shadow" / "meta" / "tables_index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        index_content1 = f.read()

    # Second format
    result2 = format_deck(str(temp_deck))
    assert result2 == 0

    # Read CSV and index after second format
    with open(csv_path, "rb") as f:
        csv_content2 = f.read()

    with open(index_path, "r", encoding="utf-8") as f:
        index_content2 = f.read()

    # Content should be byte-identical
    assert csv_content1 == csv_content2
    assert index_content1 == index_content2


def test_format_missing_shadow_dir(capsys):
    """Test error handling when shadow directory doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        deck_path = Path(tmpdir) / "no_shadow"
        deck_path.mkdir()

        result = format_deck(str(deck_path))

        assert result == 1
        captured = capsys.readouterr()
        assert "Shadow directory not found" in captured.out
        assert "Run 'extract' command first" in captured.out


def test_format_missing_index_file(capsys):
    """Test error handling when index file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        deck_path = Path(tmpdir) / "missing_index"
        deck_path.mkdir()

        shadow_dir = deck_path / "shadow"
        shadow_dir.mkdir()

        result = format_deck(str(deck_path))

        assert result == 1
        captured = capsys.readouterr()
        assert "Index file not found" in captured.out


def test_format_missing_csv_file(temp_deck, capsys):
    """Test handling of missing CSV files."""
    # Delete CSV file
    csv_path = temp_deck / "shadow" / "tables" / "abc12345" / "fi_t_test.csv"
    csv_path.unlink()

    result = format_deck(str(temp_deck))

    # Should return error code due to missing file
    assert result == 1
    captured = capsys.readouterr()
    assert "CSV file not found" in captured.out


def test_format_sorts_by_primary_keys(temp_deck):
    """Test that format correctly sorts by primary keys."""
    csv_path = temp_deck / "shadow" / "tables" / "abc12345" / "fi_t_test.csv"

    # Format
    result = format_deck(str(temp_deck))
    assert result == 0

    # Read formatted data
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    # Check that rows are sorted by primary keys (Region, Year)
    # Expected order after sorting:
    # 1. AUS, 2030
    # 2. NSW, 2020
    # 3. QLD, 2025
    assert df["Region"].tolist() == ["AUS", "NSW", "QLD"]
    assert df["Year"].tolist() == ["2030", "2020", "2025"]


def test_format_nonexistent_deck():
    """Test error handling for nonexistent deck directory."""
    result = format_deck("/nonexistent/path")
    assert result == 1


def test_format_multiple_tables():
    """Test formatting multiple tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        deck_path = Path(tmpdir) / "multi_deck"
        deck_path.mkdir()

        shadow_dir = deck_path / "shadow"
        tables_dir = shadow_dir / "tables"
        meta_dir = shadow_dir / "meta"

        tables_dir.mkdir(parents=True)
        meta_dir.mkdir(parents=True)

        # Create index
        index = TablesIndex.create_empty(generator="test/1.0.0")

        workbook_id = "wb12345"
        workbook_dir = tables_dir / workbook_id
        workbook_dir.mkdir()

        workbook_meta = WorkbookMeta(
            workbook_id=workbook_id, source_path="test.xlsx", hash="sha256:fakehash"
        )
        index.add_workbook(workbook_meta)

        # Create multiple tables
        for i in range(3):
            table_id = f"fi_t_table_{i}"
            df = pd.DataFrame(
                {
                    "Region": ["QLD", "NSW", "AUS"],
                    "Year": ["2030", "2020", "2025"],
                    "Value": [str(i * 100), str(i * 200), str(i * 300)],
                }
            )

            csv_path = workbook_dir / f"{table_id}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8", lineterminator="\n")

            with open(csv_path, "rb") as f:
                initial_hash = hashlib.sha256(f.read()).hexdigest()

            table_meta = TableMeta(
                table_id=table_id,
                workbook_id=workbook_id,
                sheet_name="Sheet1",
                tag=f"~FI_T: Table{i}",
                tag_type="fi_t",
                logical_name=f"Table{i}",
                tag_position="A1",
                columns=["Region", "Year", "Value"],
                primary_keys=["Region", "Year"],
                row_count=3,
                csv_path=f"tables/{workbook_id}/{table_id}.csv",
                csv_sha256=initial_hash,
                extracted_at="2024-01-01T00:00:00Z",
                schema_version="veda-tags-2024",
            )
            index.add_table(table_meta)

        # Write index
        index_path = meta_dir / "tables_index.json"
        TablesIndexIO.write(index, str(index_path))

        # Format
        result = format_deck(str(deck_path))
        assert result == 0

        # Verify all tables formatted
        updated_index = TablesIndexIO.read(str(index_path))
        assert len(updated_index.tables) == 3
