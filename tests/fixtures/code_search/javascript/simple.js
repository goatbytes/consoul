/**
 * Simple JavaScript file with functions and classes for testing.
 */

function calculateTotal(items) {
  let total = 0;
  for (const item of items) {
    total += item.price;
  }
  return total;
}

const processData = (data) => {
  return data.map(item => item * 2);
};

class ShoppingCart {
  constructor() {
    this.items = [];
  }

  addItem(item) {
    this.items.push(item);
  }

  getTotal() {
    return calculateTotal(this.items);
  }
}

class Product {
  constructor(name, price) {
    this.name = name;
    this.price = price;
  }

  applyDiscount(percentage) {
    this.price *= 1 - (percentage / 100);
  }
}

export { calculateTotal, processData, ShoppingCart, Product };
