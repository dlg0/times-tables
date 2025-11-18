"""Test fixtures for VEDA workbook testing."""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent
SAMPLE_DECK_DIR = FIXTURES_DIR / "sample_deck"


def get_expected_tables():
    """Load expected table metadata from expected_tables.json."""
    with open(FIXTURES_DIR / "expected_tables.json") as f:
        return json.load(f)


def get_sample_workbook_path(filename: str) -> Path:
    """Get absolute path to a sample workbook."""
    return SAMPLE_DECK_DIR / filename


def get_all_sample_workbooks() -> list[Path]:
    """Get paths to all sample workbooks in the test deck."""
    return sorted(SAMPLE_DECK_DIR.glob("*.xlsx"))


# Convenience constants
VT_BASEYEAR_PATH = get_sample_workbook_path("VT_BaseYear.xlsx")
SYSSETTINGS_PATH = get_sample_workbook_path("SysSettings.xlsx")
