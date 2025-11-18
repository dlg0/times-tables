"""Unit tests for column canonicalizer."""

import pandas as pd
import pytest

from austimes_tables.canonicalize import canonicalize_columns
from austimes_tables.veda import VedaSchema


class TestCanonicalizeColumns:
    """Tests for canonicalize_columns() function."""

    @pytest.fixture
    def schema(self):
        """Load default VEDA schema."""
        return VedaSchema()

    def test_reorder_columns_to_schema(self, schema):
        """DataFrame columns should be reordered to match schema order."""
        df = pd.DataFrame(
            {
                "Year": [2020, 2021],
                "Region": ["AUS", "AUS"],
                "Pset_PN": ["A", "B"],
                "TechName": ["TECH1", "TECH2"],
                "TechDesc": ["Description 1", "Description 2"],
            }
        )

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=True)

        valid_fields = schema.get_valid_fields("fi_t")

        df_col_canonicals = {}
        for col in df.columns:
            canonical = schema.get_canonical_name("fi_t", col)
            if canonical:
                df_col_canonicals[canonical] = col

        expected_schema_cols_in_result = []
        for field in valid_fields:
            field_lower = field.lower()
            if field_lower in df_col_canonicals:
                expected_schema_cols_in_result.append(df_col_canonicals[field_lower])
            else:
                expected_schema_cols_in_result.append(field)

        result_cols = list(result.columns)

        for i, expected_col in enumerate(expected_schema_cols_in_result[: len(valid_fields)]):
            assert result_cols[i] == expected_col, (
                f"Column at position {i} should be '{expected_col}' but got '{result_cols[i]}'"
            )

        assert len(result) == 2
        assert list(result["Year"]) == [2020, 2021]

    def test_add_missing_optional_columns(self, schema):
        """Missing optional schema columns should be added with None."""
        df = pd.DataFrame({"TechName": ["TECH1", "TECH2"], "Region": ["AUS", "AUS"]})

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=True)

        valid_fields = schema.get_valid_fields("fi_t")

        df_col_to_canonical = {}
        for col in df.columns:
            canonical = schema.get_canonical_name("fi_t", col)
            if canonical:
                df_col_to_canonical[col] = canonical

        result_col_to_canonical = {}
        for col in result.columns:
            canonical = schema.get_canonical_name("fi_t", col)
            if canonical:
                result_col_to_canonical[col] = canonical
            elif col.lower() in [f.lower() for f in valid_fields]:
                result_col_to_canonical[col] = col.lower()

        result_canonicals = set(result_col_to_canonical.values())

        for field in valid_fields:
            field_lower = field.lower()
            assert field_lower in result_canonicals, (
                f"Schema field '{field}' should be present in result (canonically)"
            )

        for col in result.columns:
            if col not in df.columns:
                assert result[col].isna().all(), (
                    f"Added column '{col}' should contain None/NaN values"
                )

    def test_keep_unknown_columns(self, schema):
        """Unknown columns should be kept at the end when keep_unknown=True."""
        df = pd.DataFrame(
            {
                "TechName": ["TECH1"],
                "Region": ["AUS"],
                "UnknownCol1": ["value1"],
                "UnknownCol2": ["value2"],
            }
        )

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=True)

        assert "UnknownCol1" in result.columns
        assert "UnknownCol2" in result.columns

        valid_fields = schema.get_valid_fields("fi_t")
        valid_fields_lower = [f.lower() for f in valid_fields]
        result_cols = list(result.columns)

        schema_cols_count = sum(1 for col in result_cols if col.lower() in valid_fields_lower)

        unknown_start_idx = schema_cols_count
        unknown_cols_in_result = result_cols[unknown_start_idx:]

        assert "UnknownCol1" in unknown_cols_in_result
        assert "UnknownCol2" in unknown_cols_in_result

    def test_drop_unknown_columns(self, schema):
        """Unknown columns should be removed when keep_unknown=False."""
        df = pd.DataFrame(
            {
                "TechName": ["TECH1"],
                "Region": ["AUS"],
                "UnknownCol1": ["value1"],
                "UnknownCol2": ["value2"],
            }
        )

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=False)

        assert "UnknownCol1" not in result.columns
        assert "UnknownCol2" not in result.columns
        assert "TechName" in result.columns
        assert "Region" in result.columns

    def test_empty_dataframe(self, schema):
        """Empty DataFrame should be handled gracefully."""
        df = pd.DataFrame()

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=True)

        assert result.empty
        assert len(result.columns) == 0

    def test_all_columns_missing(self, schema):
        """DataFrame with no schema columns should get all optional columns added."""
        df = pd.DataFrame({"UnknownCol": ["value1", "value2"]})

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=True)

        valid_fields = schema.get_valid_fields("fi_t")
        result_columns_lower = [c.lower() for c in result.columns]

        for field in valid_fields:
            field_lower = field.lower()
            assert field_lower in result_columns_lower

        assert "UnknownCol" in result.columns

    def test_all_columns_extra_drop(self, schema):
        """DataFrame with only unknown columns should be empty when keep_unknown=False."""
        df = pd.DataFrame({"UnknownCol1": ["value1"], "UnknownCol2": ["value2"]})

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=False)

        assert "UnknownCol1" not in result.columns
        assert "UnknownCol2" not in result.columns

        valid_fields = schema.get_valid_fields("fi_t")
        result_columns_lower = [c.lower() for c in result.columns]

        for field in valid_fields:
            field_lower = field.lower()
            assert field_lower in result_columns_lower

    def test_case_insensitive_matching(self, schema):
        """Column matching should be case-insensitive."""
        df = pd.DataFrame({"techname": ["TECH1"], "REGION": ["AUS"], "YeAr": [2020]})

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=True)

        assert "techname" in result.columns or "TechName" in result.columns
        assert "REGION" in result.columns or "Region" in result.columns
        assert "YeAr" in result.columns or "Year" in result.columns

    def test_preserves_data_values(self, schema):
        """Data values should be preserved after canonicalization."""
        df = pd.DataFrame(
            {
                "TechName": ["TECH1", "TECH2", "TECH3"],
                "Region": ["AUS", "NZ", "UK"],
                "Year": [2020, 2021, 2022],
                "UnknownCol": ["A", "B", "C"],
            }
        )

        result = canonicalize_columns(df, schema, "fi_t", keep_unknown=True)

        techname_col = [c for c in result.columns if c.lower() == "techname"][0]
        region_col = [c for c in result.columns if c.lower() == "region"][0]
        year_col = [c for c in result.columns if c.lower() == "year"][0]

        assert list(result[techname_col]) == ["TECH1", "TECH2", "TECH3"]
        assert list(result[region_col]) == ["AUS", "NZ", "UK"]
        assert list(result[year_col]) == [2020, 2021, 2022]
        assert list(result["UnknownCol"]) == ["A", "B", "C"]

    def test_unknown_tag_type(self, schema):
        """Unknown tag type should be handled gracefully."""
        df = pd.DataFrame({"Column1": ["value1"], "Column2": ["value2"]})

        result = canonicalize_columns(df, schema, "unknown_tag_xyz", keep_unknown=True)

        assert list(result.columns) == list(df.columns)
        assert len(result) == len(df)

    def test_different_tag_types(self, schema):
        """Should work correctly with different VEDA tag types."""
        df_process = pd.DataFrame({"TechName": ["TECH1"], "Region": ["AUS"]})

        result = canonicalize_columns(df_process, schema, "fi_process", keep_unknown=True)

        valid_fields = schema.get_valid_fields("fi_process")
        assert len(valid_fields) > 0

        result_columns_lower = [c.lower() for c in result.columns]

        for field in valid_fields:
            field_lower = field.lower()
            assert field_lower in result_columns_lower
