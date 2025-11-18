"""Golden tests for deterministic CSV writer."""

import filecmp
from pathlib import Path

import pandas as pd
import pytest

from austimes_tables.csvio import write_deterministic_csv

GOLDEN_DIR = Path(__file__).parent / "golden"


def test_csv_deterministic_across_writes(tmp_path):
    """Verify CSV output is byte-identical across multiple writes."""
    df = pd.DataFrame(
        {
            "Region": ["AUS", "NZ", "AUS"],
            "Commodity": ["COAL", "COAL", "GAS"],
            "Year": [2020, 2020, 2020],
            "Value": [100.5, 30.0, 50.2],
        }
    )

    path1 = tmp_path / "output1.csv"
    path2 = tmp_path / "output2.csv"

    write_deterministic_csv(df, str(path1), primary_keys=["Region", "Commodity", "Year"])
    write_deterministic_csv(df, str(path2), primary_keys=["Region", "Commodity", "Year"])

    # Verify files are byte-identical
    assert filecmp.cmp(path1, path2, shallow=False), "CSV files differ across writes"
    assert path1.read_bytes() == path2.read_bytes(), "Byte-level comparison failed"


def test_csv_lf_newlines(tmp_path):
    """Verify CSV uses LF (\\n) newlines, not CRLF (\\r\\n)."""
    df = pd.DataFrame(
        {
            "Region": ["AUS", "NZ"],
            "Value": [100, 200],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["Region"])

    content = path.read_bytes()

    # Verify no CRLF sequences
    assert b"\r\n" not in content, "Found CRLF newlines, expected LF only"

    # Verify LF newlines exist
    assert b"\n" in content, "No LF newlines found"


def test_csv_utf8_encoding(tmp_path):
    """Verify CSV uses UTF-8 encoding without BOM."""
    df = pd.DataFrame(
        {
            "Region": ["AUS", "EUR", "JPN"],
            "Technology": ["SOLAR_PV", "WIND_OFF", "NUCLEAR"],
            "Description": [
                "Solar photovoltaic",
                "Offshore wind turbine – 5MW",
                "原子力発電",
            ],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["Region"])

    content = path.read_bytes()

    # Verify no UTF-8 BOM
    assert not content.startswith(b"\xef\xbb\xbf"), "Found UTF-8 BOM, expected none"

    # Verify can decode as UTF-8
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        pytest.fail("Failed to decode as UTF-8")

    # Compare against golden file
    golden_path = GOLDEN_DIR / "with_unicode.csv"
    assert path.read_bytes() == golden_path.read_bytes(), "Unicode CSV differs from golden"


def test_csv_sorted_by_primary_keys(tmp_path):
    """Verify rows are sorted lexicographically by primary key tuple."""
    # Unsorted input
    df = pd.DataFrame(
        {
            "Region": ["NZ", "AUS", "AUS", "AUS", "NZ", "AUS"],
            "Commodity": ["COAL", "GAS", "COAL", "COAL", "COAL", "GAS"],
            "Year": [2030, 2030, 2030, 2020, 2020, 2020],
            "Value": [35.5, 60.1, 120.3, 100.5, 30.0, 50.2],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["Region", "Commodity", "Year"])

    # Compare against golden file (pre-sorted)
    golden_path = GOLDEN_DIR / "simple_sorted.csv"
    assert path.read_bytes() == golden_path.read_bytes(), "Sorted CSV differs from golden"

    # Verify sort order by reading back
    result_df = pd.read_csv(path)

    # Expected order: lexicographic sort by (Region, Commodity, Year)
    expected_regions = ["AUS", "AUS", "AUS", "AUS", "NZ", "NZ"]
    expected_commodities = ["COAL", "COAL", "GAS", "GAS", "COAL", "COAL"]
    expected_years = [2020, 2030, 2020, 2030, 2020, 2030]

    assert result_df["Region"].tolist() == expected_regions
    assert result_df["Commodity"].tolist() == expected_commodities
    assert result_df["Year"].tolist() == expected_years


def test_csv_canonical_column_order(tmp_path):
    """Verify columns are written in canonical order from schema."""
    # Create DataFrame with non-canonical column order
    df = pd.DataFrame(
        {
            "Value": [100, 200],
            "Year": [2020, 2030],
            "Region": ["AUS", "NZ"],
            "Commodity": ["COAL", "COAL"],
        }
    )

    # Specify canonical order
    canonical_order = ["Region", "Commodity", "Year", "Value"]

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["Region"], column_order=canonical_order)

    # Verify column order
    result_df = pd.read_csv(path)
    assert list(result_df.columns) == canonical_order, "Column order not canonical"


def test_csv_canonical_column_order_default(tmp_path):
    """Verify columns use DataFrame order when column_order not specified."""
    # Create DataFrame with specific column order
    df = pd.DataFrame(
        {
            "Region": ["AUS", "NZ"],
            "Commodity": ["COAL", "COAL"],
            "Year": [2020, 2030],
            "Value": [100, 200],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["Region"])

    # Verify column order matches DataFrame
    result_df = pd.read_csv(path)
    assert list(result_df.columns) == ["Region", "Commodity", "Year", "Value"]


def test_csv_quote_minimal(tmp_path):
    """Verify QUOTE_MINIMAL (only quote when necessary)."""
    df = pd.DataFrame(
        {
            "ID": [1, 2, 3, 4, 5],
            "Name": [
                "Simple",
                "With, comma",
                "With space",
                'With "quotes"',
                "With\nnewline",
            ],
            "Description": [
                "No special chars",
                "Contains comma",
                "No quotes needed",
                "Contains quotes",
                "Contains newline",
            ],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["ID"])

    content = path.read_text()

    # Verify simple values are not quoted
    assert "Simple,No special chars" in content or "1,Simple" in content

    # Verify values with commas are quoted
    assert '"With, comma"' in content

    # Verify values with quotes are quoted and escaped
    assert 'With ""quotes""' in content

    # Compare against golden file
    golden_path = GOLDEN_DIR / "quote_minimal.csv"
    assert path.read_bytes() == golden_path.read_bytes(), "Quote minimal CSV differs from golden"


def test_csv_empty_for_null(tmp_path):
    """Verify NULL values (None/NaN) are written as empty strings."""
    df = pd.DataFrame(
        {
            "Region": ["A", "B", "C"],
            "Process": ["PROC1", "PROC2", "PROC3"],
            "Value": [100.0, None, 300.5],
            "Comment": ["Initial value", "Missing data", None],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["Region"])

    content = path.read_text()

    # Verify empty strings for nulls (no "NaN", "None", etc.)
    assert "NaN" not in content, "Found 'NaN' in CSV, expected empty string"
    assert "None" not in content, "Found 'None' in CSV, expected empty string"

    # Verify golden file match
    golden_path = GOLDEN_DIR / "with_nulls.csv"
    assert path.read_bytes() == golden_path.read_bytes(), "Null CSV differs from golden"


def test_csv_case_sensitive_sort(tmp_path):
    """Verify lexicographic sort is case-sensitive."""
    df = pd.DataFrame(
        {
            "Region": ["b", "B", "a", "A", "c", "C"],
            "Value": [2, 20, 1, 10, 3, 30],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["Region"])

    result_df = pd.read_csv(path)

    # Case-sensitive lexicographic sort: A, B, C, a, b, c (uppercase before lowercase)
    expected_regions = ["A", "B", "C", "a", "b", "c"]
    assert result_df["Region"].tolist() == expected_regions, "Sort not case-sensitive"


def test_csv_multi_key_sort(tmp_path):
    """Verify multi-column primary key sort works correctly."""
    df = pd.DataFrame(
        {
            "Region": ["AUS", "AUS", "NZ", "NZ", "AUS", "NZ"],
            "Tech": ["B", "A", "B", "A", "C", "C"],
            "Year": [2030, 2020, 2020, 2030, 2020, 2030],
            "Value": [6, 5, 3, 4, 1, 2],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["Region", "Tech", "Year"])

    result_df = pd.read_csv(path)

    # Expected order: sort by (Region, Tech, Year) lexicographically
    # AUS/A/2020, AUS/B/2030, AUS/C/2020, NZ/A/2030, NZ/B/2020, NZ/C/2030
    expected_values = [5, 6, 1, 4, 3, 2]
    assert result_df["Value"].tolist() == expected_values, "Multi-key sort incorrect"


def test_csv_preserves_numeric_precision(tmp_path):
    """Verify numeric values are written with appropriate precision."""
    df = pd.DataFrame(
        {
            "ID": [1, 2, 3],
            "Value": [100.5, 30.0, 50.2],
            "Integer": [10, 20, 30],
        }
    )

    path = tmp_path / "output.csv"
    write_deterministic_csv(df, str(path), primary_keys=["ID"])

    # Read back and verify precision
    result_df = pd.read_csv(path)

    assert result_df["Value"].tolist() == [100.5, 30.0, 50.2]
    assert result_df["Integer"].tolist() == [10, 20, 30]
