# Code Search Test Fixtures

This directory contains test fixtures for the code_search tool's integration tests.

## Directory Structure

```
code_search/
├── python/
│   ├── simple.py          # Basic functions and classes
│   ├── nested.py          # Nested classes and methods
│   └── syntax_error.py    # Intentional syntax errors
├── javascript/
│   ├── simple.js          # Functions and ES6 classes
│   └── classes.js         # Class inheritance and methods
├── go/
│   └── simple.go          # Functions, structs, and methods
└── README.md              # This file
```

## Purpose

These fixtures are used to test:
- Multi-language AST parsing
- Symbol extraction (functions, classes, methods)
- Error handling (syntax errors, unsupported files)
- Search functionality (name matching, type filtering)
- Cache performance

## Adding New Languages

To add support for a new language:
1. Create a directory named after the language
2. Add at least one simple fixture file with:
   - Functions
   - Classes/Structs
   - Methods
3. Update integration tests to include the new language
