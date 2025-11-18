# Test Fixtures

This directory contains minimal but representative VEDA workbook fixtures for testing.

## Directory Structure

```
tests/fixtures/
├── sample_deck/          # Main test deck directory
│   ├── VT_BaseYear.xlsx  # Base year data with processes, commodities, parameters
│   └── SysSettings.xlsx  # System settings (start/end year, regions)
├── expected_tables.json  # Expected extraction metadata
├── generate_fixtures.py  # Script to regenerate fixtures
└── README.md            # This file
```

## Fixture Contents

### VT_BaseYear.xlsx

**Sheet: Processes**
- Tag: `~FI_PROCESS`
- Columns: TechName, TechDesc, Sets, PrimaryCG, Region
- Rows: 3 processes (coal, gas, wind)
- Tests: Basic process extraction, primary key sorting

**Sheet: Commodities**
- Tag: `~FI_COMM`
- Columns: CommName, CommDesc, CSet, CTSLvl
- Rows: 3 commodities (electricity, coal, gas)
- Tests: Commodity extraction, simple primary keys

**Sheet: Parameters**
- Tag: `~FI_T: BaseParameters`
- Columns: Region, TechName, Attribute, Commodity, 2020, 2025, 2030
- Rows: 7 parameter rows across 2 regions
- Tests: Composite primary keys, year columns, logical names

### SysSettings.xlsx

**Sheet: Settings**
- Tags: `~STARTYEAR`, `~ENDYEAR`, `~ACTIVEPDEF`
- Single-value tags (not tabular)
- Tests: Non-tabular tag handling

**Sheet: Regions**
- Tag: `~BOOK_REGIONS`
- Columns: Region
- Rows: 2 regions (REG1, REG2)
- Tests: Simple list extraction

## Test Coverage

These fixtures enable testing:
- ✅ Multi-table extraction from single workbook
- ✅ Multiple workbooks in same deck
- ✅ Logical names in tags (`~FI_T: BaseParameters`)
- ✅ Composite primary keys (Region + TechName + Attribute + Commodity)
- ✅ Year columns (2020, 2025, 2030)
- ✅ Single-value vs. tabular tags
- ✅ Cross-region data sorting
- ✅ Deterministic CSV output

## Data Characteristics

- **Regions**: REG1, REG2
- **Years**: 2020, 2025, 2030
- **Total rows**: ~15 data rows across all tables
- **File size**: <20KB total (minimal for fast tests)

## Regenerating Fixtures

To regenerate all fixtures:

```bash
python tests/fixtures/generate_fixtures.py
```

This will overwrite existing fixtures with clean, deterministic versions.

## Validation Reference

See `expected_tables.json` for:
- Expected table IDs
- Expected column names
- Expected row counts
- Expected primary keys

Use this for assertions in unit tests.
