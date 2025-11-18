"""Tests for deterministic row sorting."""

import pandas as pd

from austimes_tables.sorting import sort_by_primary_keys


def test_sort_single_pk():
    """Test sorting by single primary key column."""
    df = pd.DataFrame({"region": ["Z", "A", "M", "B"], "value": [1, 2, 3, 4]})

    result = sort_by_primary_keys(df, ["region"])

    assert result["region"].tolist() == ["A", "B", "M", "Z"]
    assert result["value"].tolist() == [2, 4, 3, 1]


def test_sort_multiple_pks():
    """Test sorting by composite primary key (lexicographic tuple ordering)."""
    df = pd.DataFrame(
        {
            "region": ["USA", "USA", "CHN", "CHN"],
            "year": ["2030", "2020", "2030", "2020"],
            "value": [10, 20, 30, 40],
        }
    )

    result = sort_by_primary_keys(df, ["region", "year"])

    expected_regions = ["CHN", "CHN", "USA", "USA"]
    expected_years = ["2020", "2030", "2020", "2030"]
    expected_values = [40, 30, 20, 10]

    assert result["region"].tolist() == expected_regions
    assert result["year"].tolist() == expected_years
    assert result["value"].tolist() == expected_values


def test_sort_case_sensitive():
    """Test case-sensitive string sorting."""
    df = pd.DataFrame({"code": ["a", "B", "C", "b", "A"], "value": [1, 2, 3, 4, 5]})

    result = sort_by_primary_keys(df, ["code"])

    assert result["code"].tolist() == ["A", "B", "C", "a", "b"]
    assert result["value"].tolist() == [5, 2, 3, 1, 4]


def test_sort_nulls_last():
    """Test that None/NaN values sort last."""
    df = pd.DataFrame({"region": ["A", None, "B", pd.NA, "C"], "value": [1, 2, 3, 4, 5]})

    result = sort_by_primary_keys(df, ["region"])

    first_three = result["region"].iloc[:3].tolist()
    assert first_three == ["A", "B", "C"]

    last_two_values = result["value"].iloc[3:].tolist()
    assert set(last_two_values) == {2, 4}


def test_sort_deterministic():
    """Test that sorting produces identical results each time."""
    df = pd.DataFrame(
        {
            "region": ["Z", "A", "M", "B", "Y"],
            "year": ["2020", "2030", "2020", "2030", "2020"],
            "value": [1, 2, 3, 4, 5],
        }
    )

    result1 = sort_by_primary_keys(df, ["region", "year"])
    result2 = sort_by_primary_keys(df, ["region", "year"])

    pd.testing.assert_frame_equal(result1, result2)


def test_sort_empty_dataframe():
    """Test sorting empty DataFrame returns empty without error."""
    df = pd.DataFrame(columns=["region", "year", "value"])

    result = sort_by_primary_keys(df, ["region", "year"])

    assert result.empty
    assert result.columns.tolist() == ["region", "year", "value"]


def test_sort_no_primary_keys():
    """Test sorting with no primary keys returns original order."""
    df = pd.DataFrame({"region": ["Z", "A", "M"], "value": [1, 2, 3]})

    result = sort_by_primary_keys(df, [])

    assert result["region"].tolist() == ["Z", "A", "M"]
    assert result["value"].tolist() == [1, 2, 3]


def test_sort_numeric_pk_as_string():
    """Test that numeric PK values are converted to strings for sorting."""
    df = pd.DataFrame({"year": [2030, 2020, 2025, 100], "value": [10, 20, 30, 40]})

    result = sort_by_primary_keys(df, ["year"])

    assert result["year"].tolist() == ["100", "2020", "2025", "2030"]
    assert result["value"].tolist() == [40, 20, 30, 10]


def test_sort_does_not_modify_original():
    """Test that sorting returns a new DataFrame without modifying original."""
    df = pd.DataFrame({"region": ["Z", "A", "M"], "value": [1, 2, 3]})
    original_order = df["region"].tolist()

    result = sort_by_primary_keys(df, ["region"])

    assert df["region"].tolist() == original_order
    assert result["region"].tolist() == ["A", "M", "Z"]


def test_sort_mixed_types():
    """Test sorting with mixed types in PK column."""
    df = pd.DataFrame({"code": [100, "A", 20, "B", 5], "value": [1, 2, 3, 4, 5]})

    result = sort_by_primary_keys(df, ["code"])

    assert result["code"].tolist() == ["100", "20", "5", "A", "B"]
    assert result["value"].tolist() == [1, 3, 5, 2, 4]
