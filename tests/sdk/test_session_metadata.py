"""Tests for SessionMetadata dataclass and serialization."""

from __future__ import annotations

from consoul.sdk.models import SessionMetadata


class TestSessionMetadataBasics:
    """Test basic SessionMetadata functionality."""

    def test_default_initialization(self) -> None:
        """SessionMetadata initializes with sensible defaults."""
        metadata = SessionMetadata()

        assert metadata.user_id is None
        assert metadata.tenant_id is None
        assert metadata.namespace is None
        assert metadata.tags == []
        assert metadata.custom == {}
        assert metadata.schema_version == "1.0"

    def test_initialization_with_values(self) -> None:
        """SessionMetadata accepts all optional values."""
        metadata = SessionMetadata(
            user_id="alice",
            tenant_id="acme",
            namespace="acme:alice:",
            tags=["vip", "beta"],
            custom={"plan": "enterprise", "quota": 1000},
            schema_version="1.1",
        )

        assert metadata.user_id == "alice"
        assert metadata.tenant_id == "acme"
        assert metadata.namespace == "acme:alice:"
        assert metadata.tags == ["vip", "beta"]
        assert metadata.custom == {"plan": "enterprise", "quota": 1000}
        assert metadata.schema_version == "1.1"


class TestSessionMetadataSerialization:
    """Test SessionMetadata to/from dict conversion."""

    def test_to_dict_basic(self) -> None:
        """to_dict() returns correct dict structure."""
        metadata = SessionMetadata(user_id="alice", tenant_id="acme")
        result = metadata.to_dict()

        assert result["user_id"] == "alice"
        assert result["tenant_id"] == "acme"
        assert result["namespace"] is None
        assert result["tags"] == []
        assert result["custom"] == {}
        assert result["schema_version"] == "1.0"

    def test_to_dict_with_custom_data(self) -> None:
        """to_dict() preserves custom data."""
        metadata = SessionMetadata(
            user_id="bob",
            custom={"preference": {"theme": "dark"}, "count": 42},
        )
        result = metadata.to_dict()

        assert result["custom"]["preference"]["theme"] == "dark"
        assert result["custom"]["count"] == 42

    def test_from_dict_basic(self) -> None:
        """from_dict() creates correct SessionMetadata."""
        data = {
            "user_id": "charlie",
            "tenant_id": "corp",
            "namespace": "corp:charlie:",
            "tags": ["admin"],
            "custom": {"role": "admin"},
            "schema_version": "1.0",
        }
        metadata = SessionMetadata.from_dict(data)

        assert metadata.user_id == "charlie"
        assert metadata.tenant_id == "corp"
        assert metadata.namespace == "corp:charlie:"
        assert metadata.tags == ["admin"]
        assert metadata.custom == {"role": "admin"}

    def test_from_dict_missing_fields(self) -> None:
        """from_dict() handles missing optional fields."""
        data = {"user_id": "dave"}
        metadata = SessionMetadata.from_dict(data)

        assert metadata.user_id == "dave"
        assert metadata.tenant_id is None
        assert metadata.namespace is None
        assert metadata.tags == []
        assert metadata.custom == {}
        assert metadata.schema_version == "1.0"

    def test_from_dict_empty(self) -> None:
        """from_dict() handles empty dict."""
        metadata = SessionMetadata.from_dict({})

        assert metadata.user_id is None
        assert metadata.tenant_id is None

    def test_round_trip(self) -> None:
        """to_dict/from_dict round-trips correctly."""
        original = SessionMetadata(
            user_id="eve",
            tenant_id="startup",
            namespace="startup:eve:",
            tags=["founder", "vip"],
            custom={"equity": 0.15, "settings": {"notifications": True}},
            schema_version="2.0",
        )

        serialized = original.to_dict()
        restored = SessionMetadata.from_dict(serialized)

        assert restored.user_id == original.user_id
        assert restored.tenant_id == original.tenant_id
        assert restored.namespace == original.namespace
        assert restored.tags == original.tags
        assert restored.custom == original.custom
        assert restored.schema_version == original.schema_version


class TestSessionMetadataTags:
    """Test SessionMetadata tag handling."""

    def test_tags_are_mutable(self) -> None:
        """Tags list can be modified after creation."""
        metadata = SessionMetadata(tags=["initial"])
        metadata.tags.append("added")

        assert "added" in metadata.tags

    def test_tags_isolation(self) -> None:
        """Each instance has its own tags list."""
        m1 = SessionMetadata()
        m2 = SessionMetadata()

        m1.tags.append("tag1")

        assert "tag1" not in m2.tags


class TestSessionMetadataCustomData:
    """Test SessionMetadata custom data handling."""

    def test_custom_nested_data(self) -> None:
        """custom field handles nested data structures."""
        metadata = SessionMetadata(custom={"level1": {"level2": {"value": [1, 2, 3]}}})

        assert metadata.custom["level1"]["level2"]["value"] == [1, 2, 3]

    def test_custom_data_types(self) -> None:
        """custom field handles various Python types."""
        metadata = SessionMetadata(
            custom={
                "string": "hello",
                "integer": 42,
                "float": 3.14,
                "boolean": True,
                "null": None,
                "list": [1, "two", 3.0],
                "nested": {"key": "value"},
            }
        )

        assert metadata.custom["string"] == "hello"
        assert metadata.custom["integer"] == 42
        assert metadata.custom["float"] == 3.14
        assert metadata.custom["boolean"] is True
        assert metadata.custom["null"] is None
        assert metadata.custom["list"] == [1, "two", 3.0]
        assert metadata.custom["nested"]["key"] == "value"
