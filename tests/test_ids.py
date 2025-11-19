"""Unit tests for stable ID generation.

Tests verify deterministic, unique, and stable identifiers for workbooks and tables.
"""

from times_tables.ids import generate_table_id, generate_workbook_id


class TestWorkbookID:
    """Test workbook_id generation from file paths."""

    def test_deterministic_workbook_id(self):
        """Same file path should generate same workbook_id."""
        wid1 = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        wid2 = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        assert wid1 == wid2

    def test_workbook_id_format(self):
        """Workbook ID should be non-empty string."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        assert isinstance(wid, str)
        assert len(wid) > 0

    def test_different_files_different_ids(self):
        """Different files should generate different workbook_ids."""
        wid_a = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        wid_b = generate_workbook_id("tests/fixtures/sample_deck/SysSettings.xlsx")
        assert wid_a != wid_b

    def test_workbook_id_from_filename(self):
        """Workbook ID should be derived from filename stem."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        # Should be the filename without extension
        assert wid == "VT_BaseYear"


class TestTableID:
    """Test table_id generation from metadata."""

    def test_table_id_with_logical_name(self):
        """table_id with logical name should use workbook__sheet__type__name format (normalized)."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid = generate_table_id(
            tag_type="fi_t",
            logical_name="BaseParameters",
            workbook_id=wid,
            sheet_name="Parameters",
            tag_position="B5",
        )
        # Format: workbook_id__sheet_name__TAG_TYPE__logical_name (all normalized to lowercase)
        assert tid == "VT_BaseYear__parameters__FI_T__baseparameters"

    def test_deterministic_table_id(self):
        """Same inputs should generate same table_id."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid1 = generate_table_id(
            tag_type="fi_t",
            logical_name="BaseParameters",
            workbook_id=wid,
            sheet_name="Parameters",
            tag_position="B5",
        )
        tid2 = generate_table_id(
            tag_type="fi_t",
            logical_name="BaseParameters",
            workbook_id=wid,
            sheet_name="Parameters",
            tag_position="B5",
        )
        assert tid1 == tid2

    def test_table_id_without_logical_name(self):
        """table_id without logical name should use workbook__sheet__type format (normalized)."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid = generate_table_id(
            tag_type="fi_process",
            logical_name=None,
            workbook_id=wid,
            sheet_name="Processes",
            tag_position="A1",
            veda_tag_text="~FI_PROCESS",
        )
        # Format without logical name: workbook_id__sheet_name__TAG_TYPE (sheet normalized)
        assert tid == "VT_BaseYear__processes__FI_PROCESS"

    def test_name_normalization_case_converted(self):
        """Logical names are normalized to lowercase."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid_upper = generate_table_id(
            tag_type="fi_t",
            logical_name="UPPERCASE_NAME",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        tid_lower = generate_table_id(
            tag_type="fi_t",
            logical_name="uppercase_name",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        # Case is normalized, so these should be the same
        assert tid_upper == tid_lower
        assert tid_upper == "VT_BaseYear__sheet1__FI_T__uppercase_name"
        assert tid_lower == "VT_BaseYear__sheet1__FI_T__uppercase_name"

    def test_name_whitespace_normalized(self):
        """Whitespace in logical names is collapsed and converted to underscores."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid1 = generate_table_id(
            tag_type="fi_t",
            logical_name="Multi  Space   Name",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        tid2 = generate_table_id(
            tag_type="fi_t",
            logical_name="Multi Space Name",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        # Whitespace is normalized, so different whitespace = same ID
        assert tid1 == tid2
        assert tid1 == "VT_BaseYear__sheet1__FI_T__multi_space_name"

    def test_stable_across_position_moves(self):
        """ID is stable across position moves within same sheet."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid_original = generate_table_id(
            tag_type="fi_t",
            logical_name="BaseParameters",
            workbook_id=wid,
            sheet_name="Parameters",
            tag_position="B5",
        )
        tid_moved = generate_table_id(
            tag_type="fi_t",
            logical_name="BaseParameters",
            workbook_id=wid,
            sheet_name="Parameters",  # Same sheet
            tag_position="Z99",  # Different position
        )
        # Position doesn't matter - IDs should be identical
        assert tid_original == tid_moved

        # But different sheet = different ID (includes sheet in ID)
        tid_different_sheet = generate_table_id(
            tag_type="fi_t",
            logical_name="BaseParameters",
            workbook_id=wid,
            sheet_name="DifferentSheet",
            tag_position="B5",
        )
        assert tid_original != tid_different_sheet

    def test_different_tag_types_different_ids(self):
        """Different tag types should generate different table_ids."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid_fi_t = generate_table_id(
            tag_type="fi_t",
            logical_name="Parameters",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        tid_fi_process = generate_table_id(
            tag_type="fi_process",
            logical_name="Parameters",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        assert tid_fi_t != tid_fi_process
        assert tid_fi_t == "VT_BaseYear__sheet1__FI_T__parameters"
        assert tid_fi_process == "VT_BaseYear__sheet1__FI_PROCESS__parameters"

    def test_different_logical_names_different_ids(self):
        """Different logical names should generate different table_ids."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid_a = generate_table_id(
            tag_type="fi_t",
            logical_name="TableA",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        tid_b = generate_table_id(
            tag_type="fi_t",
            logical_name="TableB",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        assert tid_a != tid_b

    def test_hash_based_id_deterministic(self):
        """Hash-based IDs (no logical name) should be deterministic."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid1 = generate_table_id(
            tag_type="fi_process",
            logical_name=None,
            workbook_id=wid,
            sheet_name="Processes",
            tag_position="A1",
            veda_tag_text="~FI_PROCESS",
        )
        tid2 = generate_table_id(
            tag_type="fi_process",
            logical_name=None,
            workbook_id=wid,
            sheet_name="Processes",
            tag_position="A1",
            veda_tag_text="~FI_PROCESS",
        )
        assert tid1 == tid2

    def test_same_veda_tag_text_same_id(self):
        """Same VEDA tag text (no logical name) generates same ID (veda_tag_text not used)."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid1 = generate_table_id(
            tag_type="fi_process",
            logical_name=None,
            workbook_id=wid,
            sheet_name="Processes",
            tag_position="A1",
            veda_tag_text="~FI_PROCESS:SetA",
        )
        tid2 = generate_table_id(
            tag_type="fi_process",
            logical_name=None,
            workbook_id=wid,
            sheet_name="Processes",
            tag_position="A1",
            veda_tag_text="~FI_PROCESS:SetB",  # Different tag text
        )
        # Current impl doesn't use veda_tag_text, so these are the same
        assert tid1 == tid2
        assert tid1 == "VT_BaseYear__processes__FI_PROCESS"

    def test_special_characters_in_logical_name(self):
        """Special characters in logical name are normalized to underscores."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid = generate_table_id(
            tag_type="fi_t",
            logical_name="Table-With/Special:Chars!",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        # Special chars are converted to underscores, lowercase applied
        assert tid == "VT_BaseYear__sheet1__FI_T__table_with_special_chars_"
