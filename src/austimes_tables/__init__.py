"""AusTIMES VEDA Table CLI - Git-friendly table extraction and validation."""

try:
    from importlib.metadata import version

    __version__ = version("austimes-tables")
except Exception:
    __version__ = "unknown"
