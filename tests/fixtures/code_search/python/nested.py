"""Python file with nested classes and methods for testing."""


class OuterClass:
    """Outer class with nested classes."""

    def outer_method(self):
        """Outer class method."""
        pass

    class NestedClass:
        """Nested class inside OuterClass."""

        def nested_method(self):
            """Nested class method."""
            pass

        def another_nested_method(self):
            """Another nested method."""
            return "nested"


def helper_function():
    """Helper function at module level."""
    return True
