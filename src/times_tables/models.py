"""Data models for AusTIMES VEDA Table CLI.

This module defines the core data structures for the tables_index.json file
and related metadata.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WorkbookMeta:
    """Metadata for a single Excel workbook.

    Attributes:
        workbook_id: 8-char Blake2b hash prefix of normalized filename
        source_path: Relative path to Excel file from deck root
        hash: Full file hash (sha256:...) for content verification
    """

    workbook_id: str
    source_path: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkbookMeta":
        """Create from dictionary loaded from JSON."""
        return cls(
            workbook_id=data["workbook_id"], source_path=data["source_path"], hash=data["hash"]
        )


@dataclass
class TableMeta:
    """Metadata for a single VEDA table.

    Attributes:
        table_id: Stable table ID derived from tag and logical name
        workbook_id: Foreign key to workbooks section
        sheet_name: Excel sheet name where table was found
        tag: Original VEDA tag (e.g., "~FI_T: BaseParameters")
        tag_type: Normalized tag type (e.g., "fi_t")
        logical_name: Logical name from tag (None if no logical name)
        tag_position: Excel cell reference of tag (e.g., "B5")
        columns: Ordered list of column names
        primary_keys: Columns forming the primary key
        row_count: Number of data rows (excluding header)
        csv_path: Relative path to CSV shadow table from the deck's shadow directory
                  (i.e., relative to deck_root / "shadow")
        csv_sha256: SHA-256 hash of CSV file content
        extracted_at: ISO 8601 timestamp when table was extracted (UTC)
        schema_version: VEDA schema version used (e.g., "veda-tags-2024")
    """

    table_id: str
    workbook_id: str
    sheet_name: str
    tag: str
    tag_type: str
    logical_name: str | None
    tag_position: str
    columns: list[str]
    primary_keys: list[str]
    row_count: int
    csv_path: str
    csv_sha256: str
    extracted_at: str
    schema_version: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TableMeta":
        """Create from dictionary loaded from JSON."""
        return cls(
            table_id=data["table_id"],
            workbook_id=data["workbook_id"],
            sheet_name=data["sheet_name"],
            tag=data["tag"],
            tag_type=data["tag_type"],
            logical_name=data["logical_name"],
            tag_position=data["tag_position"],
            columns=data["columns"],
            primary_keys=data["primary_keys"],
            row_count=data["row_count"],
            csv_path=data["csv_path"],
            csv_sha256=data["csv_sha256"],
            extracted_at=data["extracted_at"],
            schema_version=data["schema_version"],
        )

    @property
    def composite_key(self) -> str:
        """Get composite key {workbook_id}/{table_id}."""
        return f"{self.workbook_id}/{self.table_id}"


@dataclass
class TablesIndex:
    """Root structure for tables_index.json.

    This is the canonical registry of all extracted VEDA tables. It maps
    stable table identifiers to their source locations, metadata, and CSV
    shadow table paths.

    Attributes:
        version: Schema version (integer, currently 1)
        generator: Tool name and version (e.g., "times-tables/0.1.0")
        generated_at: ISO 8601 timestamp of index generation (UTC)
        workbooks: Map of workbook_id → WorkbookMeta
        tables: Map of {workbook_id}/{table_id} → TableMeta
    """

    version: int
    generator: str
    generated_at: str
    workbooks: dict[str, WorkbookMeta] = field(default_factory=dict)
    tables: dict[str, TableMeta] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "generator": self.generator,
            "generated_at": self.generated_at,
            "workbooks": {wid: wb.to_dict() for wid, wb in self.workbooks.items()},
            "tables": [table.to_dict() for table in self.tables.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TablesIndex":
        """Create from dictionary loaded from JSON."""
        # Parse tables - support both list and dict formats
        tables_data = data.get("tables", [])
        if isinstance(tables_data, list):
            tables = {
                table["composite_key"]
                if "composite_key" in table
                else f"{table['workbook_id']}/{table['table_id']}": TableMeta.from_dict(table)
                for table in tables_data
            }
        else:
            # Legacy dict format
            tables = {key: TableMeta.from_dict(table) for key, table in tables_data.items()}

        return cls(
            version=data["version"],
            generator=data["generator"],
            generated_at=data["generated_at"],
            workbooks={
                wid: WorkbookMeta.from_dict(wb) for wid, wb in data.get("workbooks", {}).items()
            },
            tables=tables,
        )

    def add_workbook(self, meta: WorkbookMeta) -> None:
        """Add or update a workbook in the index."""
        self.workbooks[meta.workbook_id] = meta

    def add_table(self, meta: TableMeta) -> None:
        """Add or update a table in the index."""
        self.tables[meta.composite_key] = meta

    def get_table(self, workbook_id: str, table_id: str) -> TableMeta | None:
        """Lookup a table by workbook_id and table_id."""
        return self.tables.get(f"{workbook_id}/{table_id}")

    def get_workbook_tables(self, workbook_id: str) -> list[TableMeta]:
        """Get all tables for a given workbook."""
        return [table for table in self.tables.values() if table.workbook_id == workbook_id]

    @staticmethod
    def create_empty(generator: str) -> "TablesIndex":
        """Create a new empty tables index."""
        return TablesIndex(
            version=1, generator=generator, generated_at=datetime.utcnow().isoformat() + "Z"
        )
