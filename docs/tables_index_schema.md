# tables_index.json Schema

## Overview

`tables_index.json` is the canonical registry of all extracted VEDA tables. It maps stable table identifiers to their source locations, metadata, and CSV shadow table paths.

**Purpose:**
- Provide stable table IDs resilient to workbook/sheet reorganization
- Enable efficient lookups and diffs without re-parsing Excel
- Track table provenance and extraction metadata
- Support validation and reporting workflows

**Location:** `shadow/tables_index.json` (generated, do NOT commit)

---

## Top-Level Structure

```json
{
  "version": 1,
  "generator": "austimes-tables/0.1.0",
  "generated_at": "2025-11-18T16:00:00Z",
  "workbooks": { ... },
  "tables": { ... }
}
```

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer | ✅ | Schema version (currently `1`) |
| `generator` | string | ✅ | Tool name and version (e.g., `"austimes-tables/0.1.0"`) |
| `generated_at` | string | ✅ | ISO 8601 timestamp of index generation (UTC) |
| `workbooks` | object | ✅ | Map of `workbook_id` → `WorkbookMeta` |
| `tables` | object | ✅ | Map of `{workbook_id}/{table_id}` → `TableMeta` |

---

## Workbooks Section

Maps workbook IDs to workbook metadata.

**Key format:** `<workbook_id>` (8-char Blake2b hash prefix of normalized filename)

**Example:**
```json
{
  "workbooks": {
    "abc12345": {
      "workbook_id": "abc12345",
      "source_path": "VT_BaseYear.xlsx",
      "hash": "sha256:a1b2c3d4e5f6..."
    },
    "def67890": {
      "workbook_id": "def67890",
      "source_path": "VT_NewTechs_2024.xlsx",
      "hash": "sha256:f6e5d4c3b2a1..."
    }
  }
}
```

### WorkbookMeta Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workbook_id` | string | ✅ | 8-char Blake2b hash prefix of normalized filename |
| `source_path` | string | ✅ | Relative path to Excel file from deck root |
| `hash` | string | ✅ | Full file hash (`sha256:...`) for content verification |

---

## Tables Section

Maps composite table keys to table metadata.

**Key format:** `{workbook_id}/{table_id}` (e.g., `"abc12345/fi_t__baseparameters"`)

**Example:**
```json
{
  "tables": {
    "abc12345/fi_t__baseparameters": {
      "table_id": "fi_t__baseparameters",
      "workbook_id": "abc12345",
      "sheet_name": "Parameters",
      "tag": "~FI_T: BaseParameters",
      "tag_type": "fi_t",
      "logical_name": "BaseParameters",
      "tag_position": "B5",
      "columns": ["region", "process", "attribute", "year", "value"],
      "primary_keys": ["region", "process", "attribute"],
      "row_count": 1247,
      "csv_path": "shadow/tables/abc12345/fi_t__baseparameters.csv",
      "csv_sha256": "def456...",
      "extracted_at": "2025-11-18T16:00:00Z",
      "schema_version": "veda-tags-2024"
    },
    "abc12345/fi_process": {
      "table_id": "fi_process",
      "workbook_id": "abc12345",
      "sheet_name": "Processes",
      "tag": "~FI_PROCESS",
      "tag_type": "fi_process",
      "logical_name": null,
      "tag_position": "A1",
      "columns": ["process", "description", "unit"],
      "primary_keys": ["process"],
      "row_count": 342,
      "csv_path": "shadow/tables/abc12345/fi_process.csv",
      "csv_sha256": "789abc...",
      "extracted_at": "2025-11-18T16:00:00Z",
      "schema_version": "veda-tags-2024"
    }
  }
}
```

### TableMeta Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table_id` | string | ✅ | Stable table ID derived from tag and logical name |
| `workbook_id` | string | ✅ | Foreign key to `workbooks` section |
| `sheet_name` | string | ✅ | Excel sheet name where table was found |
| `tag` | string | ✅ | Original VEDA tag (e.g., `"~FI_T: BaseParameters"`) |
| `tag_type` | string | ✅ | Normalized tag type (e.g., `"fi_t"`) |
| `logical_name` | string \| null | ✅ | Logical name from tag (null if no logical name) |
| `tag_position` | string | ✅ | Excel cell reference of tag (e.g., `"B5"`) |
| `columns` | array[string] | ✅ | Ordered list of column names |
| `primary_keys` | array[string] | ✅ | Columns forming the primary key |
| `row_count` | integer | ✅ | Number of data rows (excluding header) |
| `csv_path` | string | ✅ | Relative path to CSV shadow table from deck root |
| `csv_sha256` | string | ✅ | SHA-256 hash of CSV file content |
| `extracted_at` | string | ✅ | ISO 8601 timestamp when table was extracted (UTC) |
| `schema_version` | string | ✅ | VEDA schema version used (e.g., `"veda-tags-2024"`) |

---

## Constraints and Invariants

### Uniqueness
- `workbook_id` is unique within `workbooks`
- `{workbook_id}/{table_id}` composite key is unique within `tables`
- `table_id` is unique within a single workbook

### Referential Integrity
- Every `tables[*].workbook_id` must exist in `workbooks`
- Every `tables[*].csv_path` must point to a valid CSV file

### Determinism
- `workbook_id` is stable across runs for the same filename
- `table_id` is stable across runs for the same tag + logical name
- Composite key `{workbook_id}/{table_id}` remains stable even if:
  - Table moves to different sheet
  - Table moves to different cell position
  - Workbook is renamed (workbook_id changes, but table_id doesn't)

### Timestamps
- All timestamps are ISO 8601 UTC format: `YYYY-MM-DDTHH:MM:SSZ`
- `generated_at` reflects the index creation time
- `extracted_at` reflects when each individual table was extracted

---

## Example: Complete Index

```json
{
  "version": 1,
  "generator": "austimes-tables/0.1.0",
  "generated_at": "2025-11-18T16:30:45Z",
  "workbooks": {
    "abc12345": {
      "workbook_id": "abc12345",
      "source_path": "VT_BaseYear.xlsx",
      "hash": "sha256:a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
    },
    "def67890": {
      "workbook_id": "def67890",
      "source_path": "scenarios/VT_NewTechs_2024.xlsx",
      "hash": "sha256:fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321"
    }
  },
  "tables": {
    "abc12345/fi_t__baseparameters": {
      "table_id": "fi_t__baseparameters",
      "workbook_id": "abc12345",
      "sheet_name": "Parameters",
      "tag": "~FI_T: BaseParameters",
      "tag_type": "fi_t",
      "logical_name": "BaseParameters",
      "tag_position": "B5",
      "columns": ["region", "process", "attribute", "year", "value"],
      "primary_keys": ["region", "process", "attribute"],
      "row_count": 1247,
      "csv_path": "shadow/tables/abc12345/fi_t__baseparameters.csv",
      "csv_sha256": "def456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "extracted_at": "2025-11-18T16:30:45Z",
      "schema_version": "veda-tags-2024"
    },
    "abc12345/fi_process": {
      "table_id": "fi_process",
      "workbook_id": "abc12345",
      "sheet_name": "Processes",
      "tag": "~FI_PROCESS",
      "tag_type": "fi_process",
      "logical_name": null,
      "tag_position": "A1",
      "columns": ["process", "description", "unit"],
      "primary_keys": ["process"],
      "row_count": 342,
      "csv_path": "shadow/tables/abc12345/fi_process.csv",
      "csv_sha256": "789abcdef0123456789abcdef0123456789abcdef0123456789abcdef012345",
      "extracted_at": "2025-11-18T16:30:45Z",
      "schema_version": "veda-tags-2024"
    },
    "def67890/fi_t__solarpv": {
      "table_id": "fi_t__solarpv",
      "workbook_id": "def67890",
      "sheet_name": "Technologies",
      "tag": "~FI_T: SolarPV",
      "tag_type": "fi_t",
      "logical_name": "SolarPV",
      "tag_position": "A10",
      "columns": ["region", "year", "capacity", "efficiency"],
      "primary_keys": ["region", "year"],
      "row_count": 85,
      "csv_path": "shadow/tables/def67890/fi_t__solarpv.csv",
      "csv_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "extracted_at": "2025-11-18T16:30:45Z",
      "schema_version": "veda-tags-2024"
    }
  }
}
```

---

## Usage in Workflows

### Extract
1. Scan Excel workbook for VEDA tags
2. Generate `workbook_id` from filename
3. Generate `table_id` from tag + logical name
4. Extract table to CSV at `shadow/tables/{workbook_id}/{table_id}.csv`
5. Update `tables_index.json` with metadata

### Validate
1. Read `tables_index.json`
2. For each table, load CSV and validate against VEDA schema
3. Report validation errors with table provenance

### Diff
1. Read `tables_index.json` from both commits
2. Match tables by composite key `{workbook_id}/{table_id}`
3. Diff matched tables row-by-row
4. Report added/removed/modified tables

### Report
1. Read `tables_index.json` and diff results
2. Generate HTML report with:
   - Workbook summary
   - Table-level changes
   - Row-level diffs (with truncation)
   - Links to source Excel files

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2025-11-18 | Initial schema definition |

---

## References

- [PRD: AusTIMES VEDA Table CLI](AusTIMES_VEDA_CLI_PRD.txt)
- [Python Models](../src/austimes_tables/models.py)
- [ID Generation](../src/austimes_tables/ids.py)
