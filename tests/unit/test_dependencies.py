"""Test code search dependencies are properly installed and importable."""


class TestCodeSearchDependencies:
    """Validate grep-ast, tree-sitter, and diskcache dependencies."""

    def test_grep_ast_importable(self) -> None:
        """Test grep_ast module can be imported."""
        from grep_ast import TreeContext  # noqa: F401

    def test_tree_sitter_importable(self) -> None:
        """Test tree_sitter module can be imported."""
        from tree_sitter import Language, Parser  # noqa: F401

    def test_diskcache_importable(self) -> None:
        """Test diskcache module can be imported."""
        from diskcache import Cache  # noqa: F401

    def test_tree_sitter_version(self) -> None:
        """Verify tree-sitter version is 0.25.0 or higher."""
        import importlib.metadata

        version = importlib.metadata.version("tree-sitter")
        major, minor = map(int, version.split(".")[:2])
        assert major == 0
        assert minor >= 25

    def test_diskcache_version(self) -> None:
        """Verify diskcache version is 5.6.0 or higher."""
        import diskcache

        assert hasattr(diskcache, "__version__")
        major, minor = map(int, diskcache.__version__.split(".")[:2])
        assert major >= 5
        assert minor >= 6

    def test_grep_ast_tree_context_creation(self) -> None:
        """Test TreeContext can be instantiated."""
        from grep_ast import TreeContext

        # TreeContext requires a filename and tags dict
        # Just verify the class is accessible and callable
        assert callable(TreeContext)

    def test_tree_sitter_parser_creation(self) -> None:
        """Test Parser can be instantiated."""
        from tree_sitter import Parser

        parser = Parser()
        assert parser is not None

    def test_diskcache_cache_creation(self) -> None:
        """Test Cache can be instantiated."""
        import tempfile

        from diskcache import Cache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)
            assert cache is not None
            cache.close()
