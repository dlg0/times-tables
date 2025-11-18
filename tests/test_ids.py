"""Unit tests for stable ID generation.

Tests verify deterministic, unique, and stable identifiers for workbooks and tables.
"""

from austimes_tables.ids import generate_table_id, generate_workbook_id


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

    def test_workbook_id_hash_like(self):
        """Workbook ID should be hash-like (hexadecimal, reasonable length)."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        # Should be hexadecimal
        assert all(c in "0123456789abcdef" for c in wid.lower())
        # Reasonable length for hash (sha1 = 40, sha256 = 64, md5 = 32)
        assert 8 <= len(wid) <= 64


class TestTableID:
    """Test table_id generation from metadata."""

    def test_table_id_with_logical_name(self):
        """table_id with logical name should use type + normalized name."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid = generate_table_id(
            tag_type="fi_t",
            logical_name="BaseParameters",
            workbook_id=wid,
            sheet_name="Parameters",
            tag_position="B5",
        )
        assert tid.startswith("fi_t__")
        assert "baseparameters" in tid.lower()

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
        """table_id without logical name should use hash of tag text."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid = generate_table_id(
            tag_type="fi_process",
            logical_name=None,
            workbook_id=wid,
            sheet_name="Processes",
            tag_position="A1",
            veda_tag_text="~FI_PROCESS",
        )
        assert tid.startswith("fi_process__")
        # Should contain hash component since no logical name
        parts = tid.split("__")
        assert len(parts) == 2
        assert len(parts[1]) > 0

    def test_name_normalization_lowercase(self):
        """Logical names should be normalized to lowercase."""
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
        assert tid_upper == tid_lower

    def test_name_normalization_whitespace(self):
        """Multiple spaces in logical name should collapse to single underscore."""
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
        # Both should normalize to same ID
        assert "multi_space_name" in tid1.lower()
        assert tid1 == tid2

    def test_stable_across_position_moves(self):
        """Same logical name should generate same ID even if position changes."""
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
            sheet_name="DifferentSheet",  # Different sheet
            tag_position="Z99",  # Different position
        )
        # Logical name component should be same
        assert "baseparameters" in tid_original.lower()
        assert "baseparameters" in tid_moved.lower()
        # IDs should be identical (position-independent)
        assert tid_original == tid_moved

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
        assert tid_fi_t.startswith("fi_t__")
        assert tid_fi_process.startswith("fi_process__")

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

    def test_different_veda_tags_different_hash_ids(self):
        """Different VEDA tags (no logical name) should generate different hash-based IDs."""
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
            veda_tag_text="~FI_PROCESS:SetB",
        )
        assert tid1 != tid2

    def test_special_characters_in_logical_name(self):
        """Special characters in logical name should be normalized safely."""
        wid = generate_workbook_id("tests/fixtures/sample_deck/VT_BaseYear.xlsx")
        tid = generate_table_id(
            tag_type="fi_t",
            logical_name="Table-With/Special:Chars!",
            workbook_id=wid,
            sheet_name="Sheet1",
            tag_position="A1",
        )
        assert tid.startswith("fi_t__")
        # Should contain normalized version (alphanumeric + underscore)
        parts = tid.split("__")
        assert len(parts) == 2
        # Second part should be safe for filesystem/CSV
        assert all(c.isalnum() or c == "_" for c in parts[1])
