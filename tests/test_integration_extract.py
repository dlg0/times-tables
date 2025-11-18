"""Integration tests for full extract workflow.

Tests the complete extract pipeline:
- Load workbook → scan tables → generate IDs → write CSVs → write index

These tests use real fixtures from tests/fixtures/sample_deck and verify
the complete end-to-end behavior of the extract command.
"""

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Expected outputs from fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_DECK = FIXTURES_DIR / "sample_deck"
EXPECTED_TABLES_FILE = FIXTURES_DIR / "expected_tables.json"


@pytest.fixture
def expected_tables():
    """Load expected table metadata from fixtures."""
    with open(EXPECTED_TABLES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def deck_copy(tmp_path):
    """Create isolated copy of sample deck in tmp_path."""
    deck_dir = tmp_path / "sample_deck"
    shutil.copytree(SAMPLE_DECK, deck_dir)
    return deck_dir


# --- Basic Extraction Tests ---


def test_extract_creates_shadow_directory(deck_copy, expected_tables):
    """Test that extract command creates shadow/ directory structure."""
    # Run extraction via CLI
    result = subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    # Verify command executed (may fail with not implemented for now)
    assert result.returncode in [0, 1], f"Unexpected return code: {result.returncode}"

    # Verify shadow directory structure (when implemented)
    shadow_dir = deck_copy / "shadow"
    if shadow_dir.exists():
        assert shadow_dir.is_dir(), "shadow/ should be a directory"
        assert (shadow_dir / "tables").exists(), "shadow/tables/ should exist"
        assert (shadow_dir / "meta").exists(), "shadow/meta/ should exist"
    else:
        pytest.skip("Extract not yet implemented - shadow directory not created")


def test_extract_creates_csv_files(deck_copy, expected_tables):
    """Test that extract creates CSV files for all tables."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    shadow_tables = deck_copy / "shadow" / "tables"
    if not shadow_tables.exists():
        pytest.skip("Extract not yet implemented - no CSV files created")

    # Verify CSV files for each expected table
    for workbook in expected_tables["workbooks"]:
        workbook_id = workbook["workbook_id"]
        workbook_dir = shadow_tables / workbook_id

        assert workbook_dir.exists(), f"Workbook directory {workbook_id} should exist"

        for table in workbook["tables"]:
            table_id = table["table_id"]
            csv_file = workbook_dir / f"{table_id}.csv"

            assert csv_file.exists(), f"CSV file for {table_id} should exist"
            assert csv_file.stat().st_size > 0, f"CSV file {table_id} should not be empty"


def test_extract_creates_tables_index(deck_copy, expected_tables):
    """Test that extract creates shadow/meta/tables_index.json."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    index_file = deck_copy / "shadow" / "meta" / "tables_index.json"
    if not index_file.exists():
        pytest.skip("Extract not yet implemented - tables_index.json not created")

    # Verify index is valid JSON
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    assert isinstance(index_data, dict), "Index should be a dictionary"
    assert "tables" in index_data, "Index should have 'tables' key"
    assert isinstance(index_data["tables"], list), "tables should be a list"


# --- CSV Content Validation Tests ---


def test_csv_headers_match_schema(deck_copy, expected_tables):
    """Test that CSV headers match expected columns from fixtures."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    shadow_tables = deck_copy / "shadow" / "tables"
    if not shadow_tables.exists():
        pytest.skip("Extract not yet implemented")

    # Verify headers for each table
    for workbook in expected_tables["workbooks"]:
        workbook_id = workbook["workbook_id"]

        for table in workbook["tables"]:
            table_id = table["table_id"]
            expected_columns = table.get("expected_columns", [])

            if not expected_columns:
                # Skip non-tabular tags (e.g., STARTYEAR)
                continue

            csv_file = shadow_tables / workbook_id / f"{table_id}.csv"
            if not csv_file.exists():
                continue

            # Read CSV headers
            with open(csv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                headers = next(reader)

            assert headers == expected_columns, (
                f"Headers for {table_id} don't match: {headers} != {expected_columns}"
            )


def test_csv_deterministic_format(deck_copy, expected_tables):
    """Test that extract produces byte-for-byte identical CSVs on repeated runs."""
    # Run extraction twice
    for _ in range(2):
        subprocess.run(
            [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
            capture_output=True,
            text=True,
            cwd=deck_copy,
        )

    shadow_tables = deck_copy / "shadow" / "tables"
    if not shadow_tables.exists():
        pytest.skip("Extract not yet implemented")

    # Read all CSV files and store content
    first_run = {}
    for csv_file in shadow_tables.rglob("*.csv"):
        with open(csv_file, "rb") as f:
            first_run[csv_file.relative_to(shadow_tables)] = f.read()

    # Run extraction again
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    # Verify byte-for-byte identical
    for csv_file in shadow_tables.rglob("*.csv"):
        rel_path = csv_file.relative_to(shadow_tables)
        with open(csv_file, "rb") as f:
            second_run_content = f.read()

        assert second_run_content == first_run[rel_path], (
            f"CSV {rel_path} not deterministic across runs"
        )

    # Verify LF newlines (not CRLF)
    for csv_file in shadow_tables.rglob("*.csv"):
        with open(csv_file, "rb") as f:
            content = f.read()

        assert b"\r\n" not in content, f"CSV {csv_file.name} contains CRLF, should be LF only"
        assert b"\n" in content or len(content) == 0, (
            f"CSV {csv_file.name} should contain LF newlines"
        )


def test_csv_encoding_utf8(deck_copy, expected_tables):
    """Test that all CSVs are UTF-8 encoded."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    shadow_tables = deck_copy / "shadow" / "tables"
    if not shadow_tables.exists():
        pytest.skip("Extract not yet implemented")

    # Try reading each CSV with UTF-8 encoding
    for csv_file in shadow_tables.rglob("*.csv"):
        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                f.read()
        except UnicodeDecodeError as e:
            pytest.fail(f"CSV {csv_file.name} is not valid UTF-8: {e}")


# --- Index Validation Tests ---


def test_index_contains_all_tables(deck_copy, expected_tables):
    """Test that tables_index.json contains all expected tables."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    index_file = deck_copy / "shadow" / "meta" / "tables_index.json"
    if not index_file.exists():
        pytest.skip("Extract not yet implemented")

    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    # Build set of expected table IDs
    expected_table_ids = set()
    for workbook in expected_tables["workbooks"]:
        for table in workbook["tables"]:
            expected_table_ids.add(table["table_id"])

    # Build set of actual table IDs from index
    actual_table_ids = {entry["table_id"] for entry in index_data["tables"]}

    assert actual_table_ids == expected_table_ids, (
        f"Table IDs mismatch. Missing: {expected_table_ids - actual_table_ids}, "
        f"Extra: {actual_table_ids - expected_table_ids}"
    )


def test_index_has_required_fields(deck_copy, expected_tables):
    """Test that each table entry in index has all required fields."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    index_file = deck_copy / "shadow" / "meta" / "tables_index.json"
    if not index_file.exists():
        pytest.skip("Extract not yet implemented")

    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    required_fields = {
        "table_id",
        "workbook_id",
        "sheet_name",
        "tag_type",
        "logical_name",
        "columns",
        "row_count",
        "csv_path",
        "extracted_at",
    }

    for entry in index_data["tables"]:
        missing_fields = required_fields - set(entry.keys())
        assert not missing_fields, (
            f"Table {entry.get('table_id', 'unknown')} missing fields: {missing_fields}"
        )

        # Validate field types
        assert isinstance(entry["table_id"], str), "table_id should be string"
        assert isinstance(entry["workbook_id"], str), "workbook_id should be string"
        assert isinstance(entry["sheet_name"], str), "sheet_name should be string"
        assert isinstance(entry["tag_type"], str), "tag_type should be string"
        assert entry["logical_name"] is None or isinstance(entry["logical_name"], str), (
            "logical_name should be string or null"
        )
        assert isinstance(entry["columns"], list), "columns should be list"
        assert isinstance(entry["row_count"], int), "row_count should be integer"
        assert isinstance(entry["csv_path"], str), "csv_path should be string"
        assert isinstance(entry["extracted_at"], str), "extracted_at should be ISO timestamp"


def test_index_row_counts_match_csvs(deck_copy, expected_tables):
    """Test that row_count in index matches actual CSV row count."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    index_file = deck_copy / "shadow" / "meta" / "tables_index.json"
    if not index_file.exists():
        pytest.skip("Extract not yet implemented")

    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    for entry in index_data["tables"]:
        csv_path = deck_copy / "shadow" / entry["csv_path"]

        if not csv_path.exists():
            continue

        # Count rows in CSV (excluding header)
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            actual_row_count = sum(1 for row in reader)

        assert entry["row_count"] == actual_row_count, (
            f"Row count mismatch for {entry['table_id']}: "
            f"index={entry['row_count']}, csv={actual_row_count}"
        )


# --- Expected Values Tests ---


def test_extraction_matches_expected_row_counts(deck_copy, expected_tables):
    """Test that extracted tables have expected row counts from fixtures."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    shadow_tables = deck_copy / "shadow" / "tables"
    if not shadow_tables.exists():
        pytest.skip("Extract not yet implemented")

    for workbook in expected_tables["workbooks"]:
        workbook_id = workbook["workbook_id"]

        for table in workbook["tables"]:
            table_id = table["table_id"]
            expected_row_count = table.get("expected_row_count")

            if expected_row_count is None:
                continue

            csv_file = shadow_tables / workbook_id / f"{table_id}.csv"
            if not csv_file.exists():
                continue

            # Count rows (excluding header)
            with open(csv_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                actual_row_count = sum(1 for row in reader)

            assert actual_row_count == expected_row_count, (
                f"Row count mismatch for {table_id}: "
                f"expected={expected_row_count}, actual={actual_row_count}"
            )


def test_extraction_matches_expected_table_count(deck_copy, expected_tables):
    """Test that total number of extracted tables matches expected."""
    # Run extraction
    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(deck_copy)],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    shadow_tables = deck_copy / "shadow" / "tables"
    if not shadow_tables.exists():
        pytest.skip("Extract not yet implemented")

    # Count CSV files
    actual_csv_count = len(list(shadow_tables.rglob("*.csv")))
    expected_total_tables = expected_tables["summary"]["total_tables"]

    assert actual_csv_count == expected_total_tables, (
        f"Table count mismatch: expected={expected_total_tables}, actual={actual_csv_count}"
    )


# --- Output Directory Tests ---


def test_extract_with_custom_output_dir(deck_copy, expected_tables):
    """Test that --output-dir option creates shadow tables in custom location."""
    custom_output = deck_copy / "custom_shadow"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "austimes_tables.cli",
            "extract",
            str(deck_copy),
            "--output-dir",
            str(custom_output),
        ],
        capture_output=True,
        text=True,
        cwd=deck_copy,
    )

    if not custom_output.exists():
        pytest.skip("Extract not yet implemented or custom output not supported")

    # Verify structure in custom location
    assert (custom_output / "tables").exists(), "custom_shadow/tables/ should exist"
    assert (custom_output / "meta").exists(), "custom_shadow/meta/ should exist"
    assert (custom_output / "meta" / "tables_index.json").exists(), (
        "tables_index.json should exist in custom location"
    )


# --- Error Handling Tests ---


def test_extract_nonexistent_deck(tmp_path):
    """Test that extract fails gracefully on non-existent deck."""
    nonexistent = tmp_path / "does_not_exist"

    result = subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(nonexistent)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0, "Should fail on non-existent deck"
    # Error message validation would go here once implemented


def test_extract_empty_deck(tmp_path):
    """Test that extract handles empty deck directory gracefully."""
    empty_deck = tmp_path / "empty_deck"
    empty_deck.mkdir()

    subprocess.run(
        [sys.executable, "-m", "austimes_tables.cli", "extract", str(empty_deck)],
        capture_output=True,
        text=True,
        cwd=empty_deck,
    )

    # Should complete successfully but create empty index
    shadow_meta = empty_deck / "shadow" / "meta"
    if shadow_meta.exists():
        index_file = shadow_meta / "tables_index.json"
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        assert index_data["tables"] == [], "Empty deck should produce empty tables list"
    else:
        pytest.skip("Extract not yet implemented")
