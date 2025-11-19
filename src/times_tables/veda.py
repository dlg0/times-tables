"""VEDA schema loader and tag accessor for veda-tags.json."""

import json
from pathlib import Path
from typing import Any


class VedaSchema:
    """Provides access to VEDA tag definitions and field metadata from veda-tags.json."""

    def __init__(self, schema_path: str | None = None):
        """Load VEDA schema from veda-tags.json.

        Args:
            schema_path: Path to veda-tags.json. If None, loads from vendored schema.
        """
        if schema_path is None:
            vendor_dir = Path(__file__).parent / "vendor"
            schema_path = str(vendor_dir / "veda-tags.json")

        with open(schema_path, "r", encoding="utf-8") as f:
            self._tags_list: list[dict[str, Any]] = json.load(f)

        # Build fast lookup dictionaries
        self._tags_by_name: dict[str, dict[str, Any]] = {}
        self._fields_by_tag: dict[str, dict[str, dict[str, Any]]] = {}
        self._field_names_by_tag: dict[str, list[str]] = {}  # Track field 'name' values
        self._alias_to_canonical: dict[str, dict[str, str]] = {}

        self._build_indexes()

    def _build_indexes(self) -> None:
        """Build internal lookup dictionaries for fast access."""
        for tag in self._tags_list:
            tag_name = tag.get("tag_name", "").lower()
            if not tag_name:
                continue

            # Store full tag definition
            self._tags_by_name[tag_name] = tag

            # Index fields and aliases
            valid_fields = tag.get("valid_fields", [])
            fields_map: dict[str, dict[str, Any]] = {}
            field_names: list[str] = []
            alias_map: dict[str, str] = {}

            for field in valid_fields:
                field_name = field.get("name", "")
                use_name = field.get("use_name", field_name)

                if not field_name:
                    continue

                # Track original field name for get_valid_fields
                field_names.append(field_name)

                # Store field metadata by use_name for canonical lookups
                fields_map[use_name.lower()] = field

                # Map field name to use_name (if different)
                if field_name.lower() != use_name.lower():
                    alias_map[field_name.lower()] = use_name

                # Map all aliases to use_name
                for alias in field.get("aliases", []):
                    alias_map[alias.lower()] = use_name

            self._fields_by_tag[tag_name] = fields_map
            self._field_names_by_tag[tag_name] = field_names
            self._alias_to_canonical[tag_name] = alias_map

    def get_tag(self, tag_name: str) -> dict[str, Any] | None:
        """Return tag definition dict or None.

        Args:
            tag_name: Name of the VEDA tag (case-insensitive)

        Returns:
            Full tag definition dictionary or None if not found
        """
        return self._tags_by_name.get(tag_name.lower())

    def get_valid_fields(self, tag_name: str) -> list[str]:
        """Return list of valid field names (name values, not use_name).

        Args:
            tag_name: Name of the VEDA tag (case-insensitive)

        Returns:
            List of field names (original 'name' values from schema)
        """
        tag_name_lower = tag_name.lower()
        if tag_name_lower not in self._field_names_by_tag:
            return []

        return self._field_names_by_tag[tag_name_lower]

    def get_primary_keys(self, tag_name: str) -> list[str]:
        """Return fields marked with "query_field": true.

        Args:
            tag_name: Name of the VEDA tag (case-insensitive)

        Returns:
            List of field names (use_name) with query_field=true
        """
        tag_name_lower = tag_name.lower()
        if tag_name_lower not in self._fields_by_tag:
            return []

        pk_fields = []
        for use_name, field in self._fields_by_tag[tag_name_lower].items():
            if field.get("query_field", False):
                pk_fields.append(use_name)

        return pk_fields

    def resolve_alias(self, tag_name: str, field_name: str) -> str | None:
        """Map alias to canonical name (use_name).

        Args:
            tag_name: Name of the VEDA tag (case-insensitive)
            field_name: Field name or alias (case-insensitive)

        Returns:
            Canonical field name (use_name) or None if not found
        """
        tag_name_lower = tag_name.lower()
        field_name_lower = field_name.lower()

        if tag_name_lower not in self._alias_to_canonical:
            return None

        # Check if it's an alias
        if field_name_lower in self._alias_to_canonical[tag_name_lower]:
            return self._alias_to_canonical[tag_name_lower][field_name_lower]

        # Check if it's already a canonical name
        if field_name_lower in self._fields_by_tag.get(tag_name_lower, {}):
            return field_name_lower

        return None

    def get_canonical_name(self, tag_name: str, field_name: str) -> str | None:
        """Return canonical name (use_name) - accepts both aliases and canonical names.

        Args:
            tag_name: Name of the VEDA tag (case-insensitive)
            field_name: Field name or alias (case-insensitive)

        Returns:
            Canonical field name (use_name) or None if not found
        """
        tag_name_lower = tag_name.lower()
        field_name_lower = field_name.lower()

        if tag_name_lower not in self._fields_by_tag:
            return None

        # Check if it's an alias first
        if tag_name_lower in self._alias_to_canonical:
            if field_name_lower in self._alias_to_canonical[tag_name_lower]:
                return self._alias_to_canonical[tag_name_lower][field_name_lower]

        # Check if it's already a canonical name
        if field_name_lower in self._fields_by_tag[tag_name_lower]:
            return field_name_lower

        return None

    def get_field_metadata(self, tag_name: str, field_name: str) -> dict[str, Any] | None:
        """Return full field definition dict.

        Args:
            tag_name: Name of the VEDA tag (case-insensitive)
            field_name: Field name or alias (case-insensitive)

        Returns:
            Full field definition dictionary or None if not found
        """
        tag_name_lower = tag_name.lower()
        field_name.lower()

        if tag_name_lower not in self._fields_by_tag:
            return None

        # First try to resolve as alias
        canonical = self.get_canonical_name(tag_name, field_name)
        if canonical is None:
            return None

        # Return field metadata by canonical name
        return self._fields_by_tag[tag_name_lower].get(canonical.lower())

    def get_row_ignore_symbols(self, tag_name: str, field_name: str) -> list[str]:
        """Get row_ignore_symbol list for a field.

        Args:
            tag_name: Name of the VEDA tag (case-insensitive)
            field_name: Field name or alias (case-insensitive)

        Returns:
            List of row ignore symbols (e.g., ["\\I:", "*"]) or empty list
        """
        metadata = self.get_field_metadata(tag_name, field_name)
        if metadata is None:
            return []
        return metadata.get("row_ignore_symbol", [])
