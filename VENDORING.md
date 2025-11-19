# Vendoring Documentation

This document describes all vendored components from upstream projects, their licenses, and update procedures.

## Overview

The AusTIMES VEDA Table CLI vendors specific files from xl2times to maintain stability and reduce runtime dependencies. All vendored components are MIT-licensed and compatible with this project's MIT license.

## Vendored Components

### veda-tags.json

**Source Repository**: [xl2times](https://github.com/etsap-TIMES/xl2times)  
**Source File**: `xl2times/config/veda-tags.json`  
**Vendor Location**: `src/times_tables/vendor/veda-tags.json`  
**License**: MIT License  
**Copyright**: Copyright (c) 2022 ETSAP-TIMES  
**Upstream Commit**: main branch (fetched 2025-11-18)  
**Purpose**: VEDA table schema definitions including table types, valid fields, aliases, and primary key markers

#### Modifications

**None** - Used verbatim from upstream.

#### Rationale for Vendoring

- **Stability**: Schema changes in xl2times could break existing workflows
- **Reduced Dependencies**: Avoids full xl2times installation for schema-only usage
- **Version Control**: Schema changes are tracked explicitly in this repository
- **Performance**: No runtime schema fetching or parsing overhead

### Excel Extraction Patterns (Conceptual)

**Source**: xl2times table detection and extraction logic  
**Integration**: Adapted patterns for VEDA tag recognition (`~FI_T:`, `~UC_T:`, etc.)  
**License**: MIT License (xl2times)  
**Implementation**: `src/times_tables/extractor.py`

#### Modifications

**Substantial** - Reimplemented core concepts:
- VEDA tag detection patterns (regex for `~<TAG>:` format)
- Table boundary detection logic
- Column header normalization rules

#### Rationale

xl2times provides inspiration for table extraction patterns, but this project implements extraction independently for:
- Deterministic CSV output requirements
- Custom table identity tracking (table_id system)
- Git-optimized formatting and sorting

## License Information

### xl2times License

All vendored components from xl2times are licensed under the MIT License:

```
MIT License

Copyright (c) 2022 ETSAP-TIMES

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### License Compatibility

MIT ⊆ MIT: xl2times (MIT) is fully compatible with this project's MIT license. Vendored components preserve upstream copyright notices and license text per MIT License requirements.

## Attribution Requirements

When distributing this software:

1. **Include this project's LICENSE file** (MIT, AusTIMES Contributors)
2. **Include vendored component attributions** via:
   - This VENDORING.md file
   - Individual README.md files in `src/times_tables/vendor/`
3. **Preserve copyright notices** in vendored files (currently in `vendor/README.md`)

## Update Procedure

### Updating veda-tags.json

When xl2times schema changes require synchronization:

```bash
# 1. Fetch latest from xl2times
curl -O https://raw.githubusercontent.com/etsap-TIMES/xl2times/main/xl2times/config/veda-tags.json

# 2. Compare with current version
diff veda-tags.json src/times_tables/vendor/veda-tags.json

# 3. Review changes for breaking schema updates
# - New table types
# - Changed primary keys
# - Removed or renamed fields

# 4. Update vendor file
cp veda-tags.json src/times_tables/vendor/veda-tags.json

# 5. Update vendor/README.md with new commit hash and date

# 6. Run full test suite to verify compatibility
pytest

# 7. Update VENDORING.md with new upstream commit info

# 8. Document any schema changes in CHANGELOG or release notes
```

### Testing After Updates

```bash
# Determinism tests (ensure stable CSV output)
pytest tests/test_determinism.py

# Schema validation tests
pytest tests/test_schema.py

# Integration tests with sample decks
pytest tests/test_extract.py tests/test_validate.py
```

### Breaking Change Policy

If upstream schema changes introduce breaking changes:

1. **Create a bd issue** tracking the schema migration
2. **Document migration path** in release notes
3. **Consider versioning** the vendored schema if simultaneous support needed
4. **Update validation logic** to handle new schema constraints

## Version Tracking

| Component       | Upstream Version | Vendor Date | Last Updated |
|----------------|------------------|-------------|--------------|
| veda-tags.json | main branch      | 2025-11-18  | 2025-11-18   |

## Questions & Support

For questions about vendored components:
- **xl2times issues**: Report to [xl2times GitHub](https://github.com/etsap-TIMES/xl2times/issues)
- **Vendoring issues**: Create a bd issue in this project

## References

- xl2times repository: https://github.com/etsap-TIMES/xl2times
- xl2times license: https://github.com/etsap-TIMES/xl2times/blob/main/LICENSE
- VEDA-TIMES documentation: https://iea-etsap.org/
