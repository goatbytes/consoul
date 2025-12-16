"""Simple Python file with basic functions and classes for testing."""


def calculate_total(items):
    """Calculate total price of items."""
    total = 0
    for item in items:
        total += item.price
    return total


def process_data(data):
    """Process data and return results."""
    results = []
    for item in data:
        results.append(item * 2)
    return results


class ShoppingCart:
    """Shopping cart class."""

    def __init__(self):
        """Initialize shopping cart."""
        self.items = []

    def add_item(self, item):
        """Add item to cart."""
        self.items.append(item)

    def get_total(self):
        """Get cart total."""
        return calculate_total(self.items)


class Product:
    """Product class."""

    def __init__(self, name, price):
        """Initialize product."""
        self.name = name
        self.price = price

    def apply_discount(self, percentage):
        """Apply discount to product."""
        self.price *= 1 - (percentage / 100)
