"""Unit tests for VEDA schema loading and tag accessors."""

from times_tables.veda import VedaSchema


class TestVedaSchemaLoading:
    """Tests for loading and basic access to veda-tags.json schema."""

    def test_schema_loads_successfully(self):
        """Schema should load from vendored veda-tags.json without errors."""
        schema = VedaSchema()
        assert schema is not None

    def test_get_existing_tag(self):
        """Should retrieve tag definition for known tags."""
        schema = VedaSchema()
        fi_t = schema.get_tag("fi_t")
        assert fi_t is not None
        assert fi_t["tag_name"] == "fi_t"

    def test_get_multiple_tags(self):
        """Should retrieve multiple different tag definitions."""
        schema = VedaSchema()

        fi_process = schema.get_tag("fi_process")
        assert fi_process is not None
        assert fi_process["tag_name"] == "fi_process"

        fi_comm = schema.get_tag("fi_comm")
        assert fi_comm is not None
        assert fi_comm["tag_name"] == "fi_comm"

        uc_t = schema.get_tag("uc_t")
        assert uc_t is not None
        assert uc_t["tag_name"] == "uc_t"

    def test_get_unknown_tag(self):
        """Should return None for unknown tags."""
        schema = VedaSchema()
        result = schema.get_tag("unknown_nonexistent_tag")
        assert result is None


class TestValidFields:
    """Tests for retrieving valid field lists."""

    def test_get_valid_fields_fi_t(self):
        """Should return all valid field names for fi_t tag."""
        schema = VedaSchema()
        fields = schema.get_valid_fields("fi_t")

        # Based on veda-tags.json structure
        assert "attribute" in fields
        assert "process" in fields
        assert "region" in fields
        assert "commodity" in fields
        assert "commodity-in" in fields
        assert "commodity-out" in fields

    def test_get_valid_fields_fi_process(self):
        """Should return all valid field names for fi_process tag."""
        schema = VedaSchema()
        fields = schema.get_valid_fields("fi_process")

        assert "techname" in fields
        assert "region" in fields
        assert "sets" in fields
        assert "techdesc" in fields

    def test_get_valid_fields_fi_comm(self):
        """Should return all valid field names for fi_comm tag."""
        schema = VedaSchema()
        fields = schema.get_valid_fields("fi_comm")

        assert "commname" in fields
        assert "commdesc" in fields
        assert "csets" in fields

    def test_get_valid_fields_unknown_tag(self):
        """Should return empty list for unknown tags."""
        schema = VedaSchema()
        fields = schema.get_valid_fields("unknown_tag")
        assert fields == []


class TestPrimaryKeyFields:
    """Tests for identifying query_field (primary key) columns."""

    def test_get_primary_keys_uc_t(self):
        """Should return fields with query_field=true for uc_t tag."""
        schema = VedaSchema()
        pk_fields = schema.get_primary_keys("uc_t")

        # Based on veda-tags.json, uc_t has cset_cd, cset_cn, cset_set as query_fields
        assert "cset_cd" in pk_fields
        assert "cset_cn" in pk_fields
        assert "cset_set" in pk_fields

    def test_get_primary_keys_tfm_comgrp(self):
        """Should return fields with query_field=true for tfm_comgrp tag."""
        schema = VedaSchema()
        pk_fields = schema.get_primary_keys("tfm_comgrp")

        # Based on veda-tags.json
        assert "cset_cd" in pk_fields
        assert "cset_cn" in pk_fields
        assert "cset_set" in pk_fields

    def test_get_primary_keys_fi_t_no_query_fields(self):
        """Should return empty list for tags without query_field markers."""
        schema = VedaSchema()
        pk_fields = schema.get_primary_keys("fi_t")

        # fi_t has no query_field=true in its valid_fields
        assert pk_fields == []

    def test_get_primary_keys_unknown_tag(self):
        """Should return empty list for unknown tags."""
        schema = VedaSchema()
        pk_fields = schema.get_primary_keys("unknown_tag")
        assert pk_fields == []


class TestAliasResolution:
    """Tests for resolving column aliases to canonical names."""

    def test_resolve_alias_fi_t_process(self):
        """Should resolve 'techname' alias to canonical 'process' for fi_t."""
        schema = VedaSchema()
        canonical = schema.resolve_alias("fi_t", "techname")
        assert canonical == "process"

    def test_resolve_alias_fi_t_attribute(self):
        """Should resolve 'parameter' alias to canonical 'attribute' for fi_t."""
        schema = VedaSchema()
        canonical = schema.resolve_alias("fi_t", "parameter")
        assert canonical == "attribute"

    def test_resolve_alias_fi_process_techname(self):
        """Should resolve 'process' alias to canonical 'process' for fi_process."""
        schema = VedaSchema()
        # In fi_process, techname is the canonical name, process is the alias
        canonical = schema.resolve_alias("fi_process", "process")
        assert canonical == "process"  # use_name is 'process'

    def test_resolve_alias_fi_comm_commodity(self):
        """Should resolve 'commodity' alias to canonical 'commodity' for fi_comm."""
        schema = VedaSchema()
        canonical = schema.resolve_alias("fi_comm", "commodity")
        assert canonical == "commodity"  # use_name is 'commodity'

    def test_resolve_alias_not_found(self):
        """Should return None for unknown alias."""
        schema = VedaSchema()
        result = schema.resolve_alias("fi_t", "nonexistent_alias")
        assert result is None

    def test_resolve_alias_unknown_tag(self):
        """Should return None for unknown tag."""
        schema = VedaSchema()
        result = schema.resolve_alias("unknown_tag", "some_field")
        assert result is None


class TestCanonicalNames:
    """Tests for retrieving canonical column names (use_name)."""

    def test_get_canonical_name_exact_match(self):
        """Should return use_name for exact field name match."""
        schema = VedaSchema()
        canonical = schema.get_canonical_name("fi_t", "attribute")
        assert canonical == "attribute"

    def test_get_canonical_name_via_alias(self):
        """Should resolve alias to use_name."""
        schema = VedaSchema()
        canonical = schema.get_canonical_name("fi_t", "techname")
        assert canonical == "process"

    def test_get_canonical_name_process_field(self):
        """Should return canonical name for process field."""
        schema = VedaSchema()
        canonical = schema.get_canonical_name("fi_t", "process")
        assert canonical == "process"

    def test_get_canonical_name_unknown_field(self):
        """Should return None for unknown field."""
        schema = VedaSchema()
        result = schema.get_canonical_name("fi_t", "unknown_field")
        assert result is None

    def test_get_canonical_name_unknown_tag(self):
        """Should return None for unknown tag."""
        schema = VedaSchema()
        result = schema.get_canonical_name("unknown_tag", "attribute")
        assert result is None


class TestFieldMetadata:
    """Tests for retrieving additional field metadata."""

    def test_get_field_metadata_with_properties(self):
        """Should retrieve full field metadata including special properties."""
        schema = VedaSchema()
        field_meta = schema.get_field_metadata("fi_t", "region")

        assert field_meta is not None
        assert field_meta["name"] == "region"
        assert field_meta["use_name"] == "region"
        assert field_meta.get("add_if_absent") is True
        assert field_meta.get("comma-separated-list") is True

    def test_get_field_metadata_with_aliases(self):
        """Should retrieve field metadata including aliases."""
        schema = VedaSchema()
        field_meta = schema.get_field_metadata("fi_t", "attribute")

        assert field_meta is not None
        assert "aliases" in field_meta
        assert "parameter" in field_meta["aliases"]
        assert "attr" in field_meta["aliases"]

    def test_get_field_metadata_via_alias(self):
        """Should retrieve metadata when querying by alias."""
        schema = VedaSchema()
        field_meta = schema.get_field_metadata("fi_t", "techname")

        assert field_meta is not None
        assert field_meta["name"] == "process"
        assert field_meta["use_name"] == "process"

    def test_get_field_metadata_unknown_field(self):
        """Should return None for unknown field."""
        schema = VedaSchema()
        result = schema.get_field_metadata("fi_t", "unknown_field")
        assert result is None
