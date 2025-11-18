# Golden Test Files

This directory contains expected CSV outputs for deterministic CSV writer tests.

## Files

- **simple_sorted.csv** - Basic sorted table with multi-column primary keys
- **with_unicode.csv** - UTF-8 encoded file with Unicode characters (Japanese, en dash)
- **with_nulls.csv** - CSV with NULL values represented as empty strings
- **quote_minimal.csv** - CSV demonstrating QUOTE_MINIMAL quoting behavior

## Format Invariants

All golden files must maintain these properties:
- UTF-8 encoding (no BOM)
- LF newlines (`\n`) only, no CRLF (`\r\n`)
- csv.QUOTE_MINIMAL quoting
- Rows sorted by primary keys (lexicographic, case-sensitive)
- Empty string for NULL values

## Usage

Tests in `test_csv_determinism.py` compare generated CSV output against these golden files using byte-level comparison to verify deterministic formatting.
