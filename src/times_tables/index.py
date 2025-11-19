"""I/O operations for tables_index.json.

This module provides deterministic read/write operations for the tables index,
ensuring stable Git diffs with sorted keys, LF newlines, and UTF-8 encoding.
"""

import json
import os
import tempfile
from pathlib import Path

from .models import TablesIndex


class TablesIndexIO:
    """Read and write tables_index.json with deterministic formatting."""

    @staticmethod
    def write(index: TablesIndex, path: str) -> None:
        """Write TablesIndex to JSON with deterministic formatting.

        Args:
            index: TablesIndex object to serialize
            path: Output path for tables_index.json

        The output JSON is formatted deterministically:
        - Sorted keys
        - 2-space indentation
        - LF newlines only
        - UTF-8 encoding
        - Trailing newline
        - Atomic write (temp file + rename)
        """
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        data = index.to_dict()
        json_str = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
        json_str += "\n"

        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=path_obj.parent, prefix=f".{path_obj.name}.", suffix=".tmp", text=True
        )

        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(json_str)

            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def read(path: str) -> TablesIndex:
        """Read TablesIndex from JSON file.

        Args:
            path: Path to tables_index.json file

        Returns:
            Deserialized TablesIndex object

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return TablesIndex.from_dict(data)

    @staticmethod
    def create_empty(generator: str = "times-tables/0.1.0") -> TablesIndex:
        """Create a new empty TablesIndex.

        Args:
            generator: Tool name and version string

        Returns:
            New TablesIndex with version=1 and empty workbooks/tables
        """
        return TablesIndex.create_empty(generator)
