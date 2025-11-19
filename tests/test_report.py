"""Tests for report command."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from austimes_tables.commands.report import (
    compute_diff,
    escape_html,
    generate_html,
    generate_report,
)
from austimes_tables.csvio import write_deterministic_csv
from austimes_tables.index import TablesIndexIO
from austimes_tables.models import TableMeta, TablesIndex, WorkbookMeta


@pytest.fixture
def temp_decks():
    """Create two temporary decks with different tables for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create deck_a
        deck_a = tmpdir / "deck_a"
        deck_a.mkdir()
        shadow_a = deck_a / "shadow"
        tables_a = shadow_a / "tables"
        meta_a = shadow_a / "meta"
        tables_a.mkdir(parents=True)
        meta_a.mkdir(parents=True)

        # Create deck_b
        deck_b = tmpdir / "deck_b"
        deck_b.mkdir()
        shadow_b = deck_b / "shadow"
        tables_b = shadow_b / "tables"
        meta_b = shadow_b / "meta"
        tables_b.mkdir(parents=True)
        meta_b.mkdir(parents=True)

        # Create workbook directories
        workbook_id = "abc12345"
        (tables_a / workbook_id).mkdir()
        (tables_b / workbook_id).mkdir()

        # Create index_a with 2 tables
        index_a = TablesIndex.create_empty("austimes-tables/0.1.0")
        index_a.add_workbook(
            WorkbookMeta(workbook_id=workbook_id, source_path="test.xlsx", hash="sha256:abc123")
        )

        # Table 1 (in both decks, unchanged)
        table1_id = "fi_t_common"
        df1 = pd.DataFrame(
            {"Region": ["AUS", "NSW"], "Year": ["2020", "2020"], "Value": ["100", "50"]}
        )
        csv1_path = tables_a / workbook_id / f"{table1_id}.csv"
        write_deterministic_csv(df1, str(csv1_path), primary_keys=["Region", "Year"])

        table1_meta = TableMeta(
            table_id=table1_id,
            workbook_id=workbook_id,
            sheet_name="Sheet1",
            tag="~FI_T: Common",
            tag_type="fi_t",
            logical_name="Common",
            tag_position="A1",
            columns=["Region", "Year", "Value"],
            primary_keys=["Region", "Year"],
            row_count=2,
            csv_path=f"shadow/tables/{workbook_id}/{table1_id}.csv",
            csv_sha256="abc123",
            extracted_at="2024-01-01T00:00:00Z",
            schema_version="veda-tags-2024",
        )
        index_a.add_table(table1_meta)

        # Table 2 (only in deck_a, will be removed)
        table2_id = "fi_t_removed"
        df2 = pd.DataFrame({"Region": ["QLD"], "Year": ["2025"], "Value": ["200"]})
        csv2_path = tables_a / workbook_id / f"{table2_id}.csv"
        write_deterministic_csv(df2, str(csv2_path), primary_keys=["Region", "Year"])

        table2_meta = TableMeta(
            table_id=table2_id,
            workbook_id=workbook_id,
            sheet_name="Sheet2",
            tag="~FI_T: Removed",
            tag_type="fi_t",
            logical_name="Removed",
            tag_position="A1",
            columns=["Region", "Year", "Value"],
            primary_keys=["Region", "Year"],
            row_count=1,
            csv_path=f"shadow/tables/{workbook_id}/{table2_id}.csv",
            csv_sha256="def456",
            extracted_at="2024-01-01T00:00:00Z",
            schema_version="veda-tags-2024",
        )
        index_a.add_table(table2_meta)

        TablesIndexIO.write(index_a, str(meta_a / "tables_index.json"))

        # Create index_b with 2 tables
        index_b = TablesIndex.create_empty("austimes-tables/0.1.0")
        index_b.add_workbook(
            WorkbookMeta(workbook_id=workbook_id, source_path="test.xlsx", hash="sha256:abc123")
        )

        # Copy table1 to deck_b (unchanged)
        csv1b_path = tables_b / workbook_id / f"{table1_id}.csv"
        write_deterministic_csv(df1, str(csv1b_path), primary_keys=["Region", "Year"])
        index_b.add_table(table1_meta)

        # Table 3 (only in deck_b, will be added)
        table3_id = "fi_t_added"
        df3 = pd.DataFrame({"Region": ["VIC"], "Year": ["2030"], "Value": ["300"]})
        csv3_path = tables_b / workbook_id / f"{table3_id}.csv"
        write_deterministic_csv(df3, str(csv3_path), primary_keys=["Region", "Year"])

        table3_meta = TableMeta(
            table_id=table3_id,
            workbook_id=workbook_id,
            sheet_name="Sheet3",
            tag="~FI_T: Added",
            tag_type="fi_t",
            logical_name="Added",
            tag_position="A1",
            columns=["Region", "Year", "Value"],
            primary_keys=["Region", "Year"],
            row_count=1,
            csv_path=f"shadow/tables/{workbook_id}/{table3_id}.csv",
            csv_sha256="ghi789",
            extracted_at="2024-01-02T00:00:00Z",
            schema_version="veda-tags-2024",
        )
        index_b.add_table(table3_meta)

        TablesIndexIO.write(index_b, str(meta_b / "tables_index.json"))

        yield {"deck_a": str(deck_a), "deck_b": str(deck_b), "index_a": index_a, "index_b": index_b}


def test_compute_diff(temp_decks):
    """Test diff computation between two decks."""
    index_a = temp_decks["index_a"]
    index_b = temp_decks["index_b"]

    result = compute_diff(index_a, index_b)

    assert len(result["added"]) == 1
    assert "abc12345/fi_t_added" in result["added"]

    assert len(result["removed"]) == 1
    assert "abc12345/fi_t_removed" in result["removed"]

    assert len(result["unchanged"]) == 1
    assert "abc12345/fi_t_common" in result["unchanged"]

    assert len(result["modified"]) == 0


def test_compute_diff_with_modification():
    """Test diff computation with modified table."""
    # Create minimal indexes with one table that differs
    index_a = TablesIndex.create_empty("austimes-tables/0.1.0")
    index_b = TablesIndex.create_empty("austimes-tables/0.1.0")

    workbook_id = "test123"
    index_a.add_workbook(
        WorkbookMeta(workbook_id=workbook_id, source_path="test.xlsx", hash="sha256:abc")
    )
    index_b.add_workbook(
        WorkbookMeta(workbook_id=workbook_id, source_path="test.xlsx", hash="sha256:abc")
    )

    # Same table, different hash
    table_a = TableMeta(
        table_id="fi_t_test",
        workbook_id=workbook_id,
        sheet_name="Sheet1",
        tag="~FI_T: Test",
        tag_type="fi_t",
        logical_name="Test",
        tag_position="A1",
        columns=["A", "B"],
        primary_keys=["A"],
        row_count=5,
        csv_path="shadow/tables/test123/fi_t_test.csv",
        csv_sha256="hash_version_1",
        extracted_at="2024-01-01T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    table_b = TableMeta(
        table_id="fi_t_test",
        workbook_id=workbook_id,
        sheet_name="Sheet1",
        tag="~FI_T: Test",
        tag_type="fi_t",
        logical_name="Test",
        tag_position="A1",
        columns=["A", "B"],
        primary_keys=["A"],
        row_count=10,
        csv_path="shadow/tables/test123/fi_t_test.csv",
        csv_sha256="hash_version_2",
        extracted_at="2024-01-02T00:00:00Z",
        schema_version="veda-tags-2024",
    )

    index_a.add_table(table_a)
    index_b.add_table(table_b)

    result = compute_diff(index_a, index_b)

    assert len(result["modified"]) == 1
    assert "test123/fi_t_test" in result["modified"]
    assert len(result["unchanged"]) == 0


def test_generate_html_basic(temp_decks):
    """Test basic HTML generation."""
    index_a = temp_decks["index_a"]
    index_b = temp_decks["index_b"]

    diff_result = compute_diff(index_a, index_b)
    html = generate_html(temp_decks["deck_a"], temp_decks["deck_b"], diff_result, limit_rows=2000, daff_js="")

    assert "<!DOCTYPE html>" in html
    assert "<html>" in html
    assert "VEDA Deck Comparison" in html
    assert "Summary" in html
    assert "Details" in html

    # Check summary counts
    assert "Added:</span> 1 table(s)" in html
    assert "Removed:</span> 1 table(s)" in html
    assert "Unchanged:</span> 1 table(s)" in html

    # Check table names appear
    assert "fi_t_added" in html
    assert "fi_t_removed" in html


def test_generate_html_no_changes():
    """Test HTML generation when there are no changes."""
    index = TablesIndex.create_empty("austimes-tables/0.1.0")
    diff_result = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": [],
        "index_a": index,
        "index_b": index,
    }

    html = generate_html("deck_a", "deck_b", diff_result, limit_rows=2000, daff_js="")

    assert "No changes detected" in html
    assert "Added:</span> 0 table(s)" in html


def test_generate_report_success(temp_decks):
    """Test full report generation end-to-end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "report.html"

        result = generate_report(
            temp_decks["deck_a"], temp_decks["deck_b"], str(output_path), limit_rows=2000
        )

        assert result == 0
        assert output_path.exists()

        # Check file contents
        html_content = output_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_content
        assert "VEDA Deck Comparison" in html_content
        assert "fi_t_added" in html_content


def test_generate_report_missing_index(temp_decks):
    """Test report generation with missing index files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "report.html"
        nonexistent_deck = Path(tmpdir) / "nonexistent"

        result = generate_report(
            str(nonexistent_deck), temp_decks["deck_b"], str(output_path), limit_rows=2000
        )

        assert result == 1
        assert not output_path.exists()


def test_escape_html():
    """Test HTML escaping."""
    assert escape_html("plain text") == "plain text"
    assert escape_html("<script>") == "&lt;script&gt;"
    assert escape_html("a & b") == "a &amp; b"
    assert escape_html('"quotes"') == "&quot;quotes&quot;"
    assert escape_html("'apostrophe'") == "&#x27;apostrophe&#x27;"
    assert escape_html('<tag attr="value">') == "&lt;tag attr=&quot;value&quot;&gt;"


def test_html_validity(temp_decks):
    """Test that generated HTML is well-formed."""
    index_a = temp_decks["index_a"]
    index_b = temp_decks["index_b"]

    diff_result = compute_diff(index_a, index_b)
    html = generate_html(temp_decks["deck_a"], temp_decks["deck_b"], diff_result, limit_rows=2000, daff_js="")

    # Basic validation checks
    assert html.count("<html>") == 1
    assert html.count("</html>") == 1
    assert html.count("<head>") == 1
    assert html.count("</head>") == 1
    assert html.count("<body>") == 1
    assert html.count("</body>") == 1
    assert html.count("<title>") == 1
    assert html.count("</title>") == 1

    # Check for required sections
    assert "<style>" in html
    assert "</style>" in html
    assert 'class="container"' in html
    assert 'class="summary"' in html
