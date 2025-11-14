// Simple Go file with functions and structs for testing.
package main

import "fmt"

// CalculateTotal calculates the total price of items.
func CalculateTotal(items []Item) float64 {
	total := 0.0
	for _, item := range items {
		total += item.Price
	}
	return total
}

// ProcessData processes data and returns results.
func ProcessData(data []int) []int {
	results := make([]int, len(data))
	for i, item := range data {
		results[i] = item * 2
	}
	return results
}

// Item represents a product item.
type Item struct {
	Name  string
	Price float64
}

// ShoppingCart represents a shopping cart.
type ShoppingCart struct {
	Items []Item
}

// AddItem adds an item to the cart.
func (sc *ShoppingCart) AddItem(item Item) {
	sc.Items = append(sc.Items, item)
}

// GetTotal returns the cart total.
func (sc *ShoppingCart) GetTotal() float64 {
	return CalculateTotal(sc.Items)
}

// Product represents a product.
type Product struct {
	Name  string
	Price float64
}

// ApplyDiscount applies a discount to the product.
func (p *Product) ApplyDiscount(percentage float64) {
	p.Price *= 1 - (percentage / 100)
}
