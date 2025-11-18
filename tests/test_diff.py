"""Tests for diff command."""

import json

import pytest

from austimes_tables.commands.diff import _compute_diff, _load_index, diff_decks
from austimes_tables.index import TablesIndexIO
from austimes_tables.models import TableMeta, TablesIndex, WorkbookMeta


@pytest.fixture
def empty_index():
    """Create an empty tables index."""
    return TablesIndex.create_empty("austimes-tables/0.1.0")


@pytest.fixture
def sample_index_a():
    """Create sample index A with 3 tables."""
    index = TablesIndex.create_empty("austimes-tables/0.1.0")

    # Add workbook
    wb = WorkbookMeta(workbook_id="abc12345", source_path="workbook.xlsx", hash="sha256:abc123")
    index.add_workbook(wb)

    # Add tables
    table1 = TableMeta(
        table_id="table_1",
        workbook_id="abc12345",
        sheet_name="Sheet1",
        tag="~FI_T: Table1",
        tag_type="fi_t",
        logical_name="Table1",
        tag_position="B5",
        columns=["Region", "Year", "Value"],
        primary_keys=["Region", "Year"],
        row_count=10,
        csv_path="tables/abc12345/table_1.csv",
        csv_sha256="hash1_original",
        extracted_at="2025-11-18T10:00:00Z",
        schema_version="veda-tags-2024",
    )
    index.add_table(table1)

    table2 = TableMeta(
        table_id="table_2",
        workbook_id="abc12345",
        sheet_name="Sheet2",
        tag="~FI_T: Table2",
        tag_type="fi_t",
        logical_name="Table2",
        tag_position="B5",
        columns=["Tech", "Cost"],
        primary_keys=["Tech"],
        row_count=5,
        csv_path="tables/abc12345/table_2.csv",
        csv_sha256="hash2_original",
        extracted_at="2025-11-18T10:00:00Z",
        schema_version="veda-tags-2024",
    )
    index.add_table(table2)

    table3 = TableMeta(
        table_id="table_3",
        workbook_id="abc12345",
        sheet_name="Sheet3",
        tag="~FI_T: Table3",
        tag_type="fi_t",
        logical_name="Table3",
        tag_position="B5",
        columns=["X", "Y"],
        primary_keys=["X"],
        row_count=8,
        csv_path="tables/abc12345/table_3.csv",
        csv_sha256="hash3_original",
        extracted_at="2025-11-18T10:00:00Z",
        schema_version="veda-tags-2024",
    )
    index.add_table(table3)

    return index


@pytest.fixture
def sample_index_b():
    """Create sample index B with changes:
    - table_1: removed
    - table_2: modified (different hash)
    - table_3: unchanged
    - table_4: added
    """
    index = TablesIndex.create_empty("austimes-tables/0.1.0")

    # Add workbook
    wb = WorkbookMeta(workbook_id="abc12345", source_path="workbook.xlsx", hash="sha256:abc123")
    index.add_workbook(wb)

    # table_1 is removed (not added to index_b)

    # table_2 modified (different hash and row count)
    table2 = TableMeta(
        table_id="table_2",
        workbook_id="abc12345",
        sheet_name="Sheet2",
        tag="~FI_T: Table2",
        tag_type="fi_t",
        logical_name="Table2",
        tag_position="B5",
        columns=["Tech", "Cost"],
        primary_keys=["Tech"],
        row_count=7,  # Changed from 5 to 7
        csv_path="tables/abc12345/table_2.csv",
        csv_sha256="hash2_modified",  # Different hash
        extracted_at="2025-11-18T11:00:00Z",
        schema_version="veda-tags-2024",
    )
    index.add_table(table2)

    # table_3 unchanged (same hash)
    table3 = TableMeta(
        table_id="table_3",
        workbook_id="abc12345",
        sheet_name="Sheet3",
        tag="~FI_T: Table3",
        tag_type="fi_t",
        logical_name="Table3",
        tag_position="B5",
        columns=["X", "Y"],
        primary_keys=["X"],
        row_count=8,
        csv_path="tables/abc12345/table_3.csv",
        csv_sha256="hash3_original",  # Same hash
        extracted_at="2025-11-18T11:00:00Z",
        schema_version="veda-tags-2024",
    )
    index.add_table(table3)

    # table_4 added
    table4 = TableMeta(
        table_id="table_4",
        workbook_id="abc12345",
        sheet_name="Sheet4",
        tag="~FI_T: Table4",
        tag_type="fi_t",
        logical_name="Table4",
        tag_position="B5",
        columns=["A", "B", "C"],
        primary_keys=["A"],
        row_count=3,
        csv_path="tables/abc12345/table_4.csv",
        csv_sha256="hash4_new",
        extracted_at="2025-11-18T11:00:00Z",
        schema_version="veda-tags-2024",
    )
    index.add_table(table4)

    return index


def test_compute_diff_identical(sample_index_a):
    """Test diff with identical decks."""
    diff = _compute_diff("deck_a", "deck_b", sample_index_a, sample_index_a)

    assert diff["tables_added"] == []
    assert diff["tables_removed"] == []
    assert diff["tables_modified"] == []
    assert diff["summary"]["total_tables_a"] == 3
    assert diff["summary"]["total_tables_b"] == 3
    assert diff["summary"]["added"] == 0
    assert diff["summary"]["removed"] == 0
    assert diff["summary"]["modified"] == 0
    assert diff["summary"]["unchanged"] == 3


def test_compute_diff_changes(sample_index_a, sample_index_b):
    """Test diff with added/removed/modified tables."""
    diff = _compute_diff("deck_a", "deck_b", sample_index_a, sample_index_b)

    # Check added tables
    assert diff["tables_added"] == ["abc12345/table_4"]

    # Check removed tables
    assert diff["tables_removed"] == ["abc12345/table_1"]

    # Check modified tables
    assert len(diff["tables_modified"]) == 1
    modified = diff["tables_modified"][0]
    assert modified["table_id"] == "abc12345/table_2"
    assert modified["changes"]["row_count"]["a"] == 5
    assert modified["changes"]["row_count"]["b"] == 7
    assert modified["changes"]["csv_hash"]["a"] == "hash2_original"
    assert modified["changes"]["csv_hash"]["b"] == "hash2_modified"

    # Check summary
    assert diff["summary"]["total_tables_a"] == 3
    assert diff["summary"]["total_tables_b"] == 3
    assert diff["summary"]["added"] == 1
    assert diff["summary"]["removed"] == 1
    assert diff["summary"]["modified"] == 1
    assert diff["summary"]["unchanged"] == 1


def test_compute_diff_empty_to_populated(empty_index, sample_index_a):
    """Test diff from empty to populated deck."""
    diff = _compute_diff("deck_a", "deck_b", empty_index, sample_index_a)

    assert len(diff["tables_added"]) == 3
    assert diff["tables_removed"] == []
    assert diff["tables_modified"] == []
    assert diff["summary"]["total_tables_a"] == 0
    assert diff["summary"]["total_tables_b"] == 3
    assert diff["summary"]["added"] == 3
    assert diff["summary"]["unchanged"] == 0


def test_compute_diff_populated_to_empty(sample_index_a, empty_index):
    """Test diff from populated to empty deck."""
    diff = _compute_diff("deck_a", "deck_b", sample_index_a, empty_index)

    assert diff["tables_added"] == []
    assert len(diff["tables_removed"]) == 3
    assert diff["tables_modified"] == []
    assert diff["summary"]["total_tables_a"] == 3
    assert diff["summary"]["total_tables_b"] == 0
    assert diff["summary"]["removed"] == 3
    assert diff["summary"]["unchanged"] == 0


def test_load_index_missing_file(tmp_path):
    """Test loading index from non-existent deck."""
    deck_path = tmp_path / "nonexistent_deck"

    with pytest.raises(FileNotFoundError) as excinfo:
        _load_index(str(deck_path), "test_deck")

    assert "tables_index.json not found" in str(excinfo.value)


def test_load_index_success(tmp_path, sample_index_a):
    """Test successfully loading an index."""
    deck_path = tmp_path / "deck"
    index_path = deck_path / "shadow" / "meta" / "tables_index.json"
    index_path.parent.mkdir(parents=True)

    TablesIndexIO.write(sample_index_a, str(index_path))

    loaded = _load_index(str(deck_path), "test_deck")
    assert len(loaded.tables) == 3
    assert "abc12345/table_1" in loaded.tables


def test_diff_decks_to_stdout(tmp_path, sample_index_a, sample_index_b, capsys):
    """Test diff command with stdout output."""
    # Create deck A
    deck_a = tmp_path / "deck_a"
    index_a_path = deck_a / "shadow" / "meta" / "tables_index.json"
    index_a_path.parent.mkdir(parents=True)
    TablesIndexIO.write(sample_index_a, str(index_a_path))

    # Create deck B
    deck_b = tmp_path / "deck_b"
    index_b_path = deck_b / "shadow" / "meta" / "tables_index.json"
    index_b_path.parent.mkdir(parents=True)
    TablesIndexIO.write(sample_index_b, str(index_b_path))

    # Run diff
    exit_code = diff_decks(str(deck_a), str(deck_b), output=None)

    # Check exit code (1 because there are differences)
    assert exit_code == 1

    # Check stdout contains JSON
    captured = capsys.readouterr()
    diff_result = json.loads(captured.out)

    assert diff_result["summary"]["added"] == 1
    assert diff_result["summary"]["removed"] == 1
    assert diff_result["summary"]["modified"] == 1


def test_diff_decks_to_file(tmp_path, sample_index_a, sample_index_b):
    """Test diff command with file output."""
    # Create deck A
    deck_a = tmp_path / "deck_a"
    index_a_path = deck_a / "shadow" / "meta" / "tables_index.json"
    index_a_path.parent.mkdir(parents=True)
    TablesIndexIO.write(sample_index_a, str(index_a_path))

    # Create deck B
    deck_b = tmp_path / "deck_b"
    index_b_path = deck_b / "shadow" / "meta" / "tables_index.json"
    index_b_path.parent.mkdir(parents=True)
    TablesIndexIO.write(sample_index_b, str(index_b_path))

    # Output file
    output_file = tmp_path / "diff.json"

    # Run diff
    exit_code = diff_decks(str(deck_a), str(deck_b), output=str(output_file))

    # Check exit code
    assert exit_code == 1

    # Check output file exists and has valid JSON
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as f:
        diff_result = json.load(f)

    assert diff_result["summary"]["added"] == 1
    assert diff_result["summary"]["removed"] == 1
    assert diff_result["summary"]["modified"] == 1
    assert diff_result["tables_added"] == ["abc12345/table_4"]
    assert diff_result["tables_removed"] == ["abc12345/table_1"]


def test_diff_decks_identical_returns_zero(tmp_path, sample_index_a):
    """Test diff command returns 0 for identical decks."""
    # Create deck A
    deck_a = tmp_path / "deck_a"
    index_a_path = deck_a / "shadow" / "meta" / "tables_index.json"
    index_a_path.parent.mkdir(parents=True)
    TablesIndexIO.write(sample_index_a, str(index_a_path))

    # Create deck B (identical)
    deck_b = tmp_path / "deck_b"
    index_b_path = deck_b / "shadow" / "meta" / "tables_index.json"
    index_b_path.parent.mkdir(parents=True)
    TablesIndexIO.write(sample_index_a, str(index_b_path))

    # Run diff
    exit_code = diff_decks(str(deck_a), str(deck_b), output=None)

    # Check exit code (0 for no differences)
    assert exit_code == 0


def test_diff_decks_missing_index(tmp_path):
    """Test diff command with missing index file."""
    deck_a = tmp_path / "deck_a"
    deck_b = tmp_path / "deck_b"

    # Run diff (should fail)
    exit_code = diff_decks(str(deck_a), str(deck_b), output=None)

    assert exit_code == 1


def test_diff_output_structure(sample_index_a, sample_index_b):
    """Test that diff output has expected structure."""
    diff = _compute_diff("deck_a", "deck_b", sample_index_a, sample_index_b)

    # Check top-level keys
    assert "deck_a" in diff
    assert "deck_b" in diff
    assert "compared_at" in diff
    assert "tables_added" in diff
    assert "tables_removed" in diff
    assert "tables_modified" in diff
    assert "summary" in diff

    # Check summary keys
    summary = diff["summary"]
    assert "total_tables_a" in summary
    assert "total_tables_b" in summary
    assert "added" in summary
    assert "removed" in summary
    assert "modified" in summary
    assert "unchanged" in summary

    # Check compared_at is ISO 8601 format
    assert diff["compared_at"].endswith("Z")
    assert "T" in diff["compared_at"]


def test_diff_sorted_table_ids(sample_index_a, sample_index_b):
    """Test that table IDs in diff output are sorted."""
    # Create index with multiple added/removed tables
    index_c = TablesIndex.create_empty("austimes-tables/0.1.0")
    wb = WorkbookMeta(workbook_id="xyz99999", source_path="other.xlsx", hash="sha256:xyz")
    index_c.add_workbook(wb)

    # Add multiple tables in non-alphabetical order
    for table_id in ["zzz", "aaa", "mmm", "bbb"]:
        table = TableMeta(
            table_id=table_id,
            workbook_id="xyz99999",
            sheet_name="Sheet1",
            tag=f"~FI_T: {table_id}",
            tag_type="fi_t",
            logical_name=table_id,
            tag_position="B5",
            columns=["X"],
            primary_keys=["X"],
            row_count=1,
            csv_path=f"tables/xyz99999/{table_id}.csv",
            csv_sha256=f"hash_{table_id}",
            extracted_at="2025-11-18T10:00:00Z",
            schema_version="veda-tags-2024",
        )
        index_c.add_table(table)

    diff = _compute_diff("deck_a", "deck_c", sample_index_a, index_c)

    # Check that added tables are sorted
    added = diff["tables_added"]
    assert added == sorted(added)

    # Check that removed tables are sorted
    removed = diff["tables_removed"]
    assert removed == sorted(removed)
