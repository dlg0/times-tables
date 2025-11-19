"""Tests for tables_index.json I/O operations."""

import json

import pytest

from times_tables.index import TablesIndexIO
from times_tables.models import TableMeta, TablesIndex, WorkbookMeta


@pytest.fixture
def sample_index() -> TablesIndex:
    """Create a sample TablesIndex with test data."""
    index = TablesIndex(
        version=1, generator="times-tables/0.1.0", generated_at="2025-11-18T10:00:00Z"
    )

    wb = WorkbookMeta(
        workbook_id="abc12345", source_path="Workbooks/Sample.xlsx", hash="sha256:deadbeef"
    )
    index.add_workbook(wb)

    table = TableMeta(
        table_id="fi_t_params",
        workbook_id="abc12345",
        sheet_name="Data",
        tag="~FI_T: BaseParameters",
        tag_type="fi_t",
        logical_name="BaseParameters",
        tag_position="B5",
        columns=["Region", "Year", "Value"],
        primary_keys=["Region", "Year"],
        row_count=100,
        csv_path="abc12345_fi_t_params.csv",
        csv_sha256="sha256:cafe1234",
        extracted_at="2025-11-18T10:00:00Z",
        schema_version="veda-tags-2024",
    )
    index.add_table(table)

    return index


def test_write_and_read_roundtrip(tmp_path, sample_index):
    """Write and read should preserve all data."""
    json_path = tmp_path / "tables_index.json"

    TablesIndexIO.write(sample_index, str(json_path))
    loaded = TablesIndexIO.read(str(json_path))

    assert loaded.version == sample_index.version
    assert loaded.generator == sample_index.generator
    assert loaded.generated_at == sample_index.generated_at
    assert len(loaded.workbooks) == len(sample_index.workbooks)
    assert len(loaded.tables) == len(sample_index.tables)

    wb_orig = sample_index.workbooks["abc12345"]
    wb_loaded = loaded.workbooks["abc12345"]
    assert wb_loaded.workbook_id == wb_orig.workbook_id
    assert wb_loaded.source_path == wb_orig.source_path
    assert wb_loaded.hash == wb_orig.hash

    table_key = "abc12345/fi_t_params"
    table_orig = sample_index.tables[table_key]
    table_loaded = loaded.tables[table_key]
    assert table_loaded.table_id == table_orig.table_id
    assert table_loaded.workbook_id == table_orig.workbook_id
    assert table_loaded.columns == table_orig.columns
    assert table_loaded.primary_keys == table_orig.primary_keys
    assert table_loaded.row_count == table_orig.row_count


def test_write_deterministic_format(tmp_path, sample_index):
    """Writing the same index twice should produce identical files."""
    path1 = tmp_path / "index1.json"
    path2 = tmp_path / "index2.json"

    TablesIndexIO.write(sample_index, str(path1))
    TablesIndexIO.write(sample_index, str(path2))

    content1 = path1.read_bytes()
    content2 = path2.read_bytes()

    assert content1 == content2


def test_json_has_sorted_keys(tmp_path, sample_index):
    """JSON output should have sorted keys at all levels."""
    json_path = tmp_path / "tables_index.json"

    TablesIndexIO.write(sample_index, str(json_path))

    with open(json_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = json.loads(content)

    top_keys = list(data.keys())
    assert top_keys == sorted(top_keys)

    if data.get("workbooks"):
        for wb_data in data["workbooks"].values():
            wb_keys = list(wb_data.keys())
            assert wb_keys == sorted(wb_keys)

    if data.get("tables"):
        # tables is a list, not a dict
        for table_data in data["tables"]:
            table_keys = list(table_data.keys())
            assert table_keys == sorted(table_keys)


def test_json_has_lf_newlines(tmp_path, sample_index):
    """JSON output should only contain LF newlines, no CRLF."""
    json_path = tmp_path / "tables_index.json"

    TablesIndexIO.write(sample_index, str(json_path))

    raw_bytes = json_path.read_bytes()

    assert b"\r\n" not in raw_bytes
    assert b"\n" in raw_bytes


def test_json_has_trailing_newline(tmp_path, sample_index):
    """JSON file should end with a newline."""
    json_path = tmp_path / "tables_index.json"

    TablesIndexIO.write(sample_index, str(json_path))

    content = json_path.read_text(encoding="utf-8")

    assert content.endswith("\n")


def test_create_empty_index():
    """create_empty should return a valid empty index."""
    index = TablesIndexIO.create_empty("test-tool/1.0.0")

    assert index.version == 1
    assert index.generator == "test-tool/1.0.0"
    assert index.generated_at is not None
    assert index.generated_at.endswith("Z")
    assert len(index.workbooks) == 0
    assert len(index.tables) == 0


def test_create_empty_index_default_generator():
    """create_empty should use default generator if not specified."""
    index = TablesIndexIO.create_empty()

    assert index.generator == "times-tables/0.1.0"


def test_read_nonexistent_file():
    """Reading a nonexistent file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        TablesIndexIO.read("/nonexistent/path/tables_index.json")


def test_read_invalid_json(tmp_path):
    """Reading invalid JSON should raise JSONDecodeError."""
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("not valid json {")

    with pytest.raises(json.JSONDecodeError):
        TablesIndexIO.read(str(bad_json))


def test_write_creates_parent_directories(tmp_path):
    """write should create parent directories if they don't exist."""
    nested_path = tmp_path / "deeply" / "nested" / "path" / "index.json"

    index = TablesIndexIO.create_empty()
    TablesIndexIO.write(index, str(nested_path))

    assert nested_path.exists()
    loaded = TablesIndexIO.read(str(nested_path))
    assert loaded.version == 1


def test_write_overwrites_existing_file(tmp_path, sample_index):
    """write should overwrite existing file atomically."""
    json_path = tmp_path / "index.json"

    empty_index = TablesIndexIO.create_empty()
    TablesIndexIO.write(empty_index, str(json_path))

    loaded = TablesIndexIO.read(str(json_path))
    assert len(loaded.tables) == 0

    TablesIndexIO.write(sample_index, str(json_path))

    loaded = TablesIndexIO.read(str(json_path))
    assert len(loaded.tables) == 1


def test_roundtrip_with_multiple_tables(tmp_path):
    """Roundtrip should work with multiple workbooks and tables."""
    index = TablesIndex(version=1, generator="test/1.0", generated_at="2025-11-18T12:00:00Z")

    for i in range(3):
        wb = WorkbookMeta(
            workbook_id=f"wb{i:02d}00000",
            source_path=f"Workbooks/File{i}.xlsx",
            hash=f"sha256:hash{i}",
        )
        index.add_workbook(wb)

        for j in range(2):
            table = TableMeta(
                table_id=f"table_{i}_{j}",
                workbook_id=wb.workbook_id,
                sheet_name=f"Sheet{j}",
                tag=f"~TAG_{i}_{j}",
                tag_type="test_tag",
                logical_name=None,
                tag_position="A1",
                columns=["col1", "col2"],
                primary_keys=["col1"],
                row_count=10 * (i + j),
                csv_path=f"{wb.workbook_id}_table_{i}_{j}.csv",
                csv_sha256=f"sha256:table{i}{j}",
                extracted_at="2025-11-18T12:00:00Z",
                schema_version="veda-tags-2024",
            )
            index.add_table(table)

    json_path = tmp_path / "multi.json"
    TablesIndexIO.write(index, str(json_path))
    loaded = TablesIndexIO.read(str(json_path))

    assert len(loaded.workbooks) == 3
    assert len(loaded.tables) == 6

    for i in range(3):
        wb_id = f"wb{i:02d}00000"
        assert wb_id in loaded.workbooks
        assert loaded.workbooks[wb_id].source_path == f"Workbooks/File{i}.xlsx"


def test_roundtrip_with_unicode(tmp_path):
    """Roundtrip should preserve Unicode characters."""
    index = TablesIndex(
        version=1, generator="times-tables/0.1.0", generated_at="2025-11-18T10:00:00Z"
    )

    wb = WorkbookMeta(
        workbook_id="unicode01", source_path="Données/Fîchier_€.xlsx", hash="sha256:unicode"
    )
    index.add_workbook(wb)

    table = TableMeta(
        table_id="table_unicode",
        workbook_id="unicode01",
        sheet_name="Données",
        tag="~TAG: Éléments",
        tag_type="test",
        logical_name="Éléments",
        tag_position="A1",
        columns=["Région", "Année", "Valeur"],
        primary_keys=["Région"],
        row_count=5,
        csv_path="unicode01_table.csv",
        csv_sha256="sha256:test",
        extracted_at="2025-11-18T10:00:00Z",
        schema_version="veda-tags-2024",
    )
    index.add_table(table)

    json_path = tmp_path / "unicode.json"
    TablesIndexIO.write(index, str(json_path))
    loaded = TablesIndexIO.read(str(json_path))

    assert loaded.workbooks["unicode01"].source_path == "Données/Fîchier_€.xlsx"
    table_loaded = loaded.tables["unicode01/table_unicode"]
    assert table_loaded.sheet_name == "Données"
    assert table_loaded.columns == ["Région", "Année", "Valeur"]
