# tests/README.md

# Test Suite Organization

## Structure

```
tests/
├── data_engine/              # Data engine tests
│   └── test_data_engine.py   # Core data engine functionality
├── api/                      # API endpoint tests (future)
├── services/                 # Service layer tests (future)  
├── simple_test.py            # Quick manual tests
└── README.md                 # This file
```

## Running Tests

### All Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov-report=html
```

### Data Engine Tests
```bash
# All data engine tests (17 tests)
pytest tests/data_engine/ -v

# Specific test class (5 tests)
pytest tests/data_engine/test_data_engine.py::TestBasicFunctionality -v

# Single test
pytest tests/data_engine/test_data_engine.py::TestBasicFunctionality::test_engine_initialization -v

# Integration tests (2 tests)
pytest tests/data_engine/test_data_engine.py::TestIntegration -v

# Error handling tests (4 tests)  
pytest tests/data_engine/test_data_engine.py::TestErrorHandling -v
```

### Quick Tests
```bash
# Manual verification
python tests/simple_test.py

# Basic functionality only
pytest tests/data_engine/ -m "not slow" -v
```

### Test Markers
```bash
# Unit tests only
pytest -m unit

# Integration tests only  
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Adding New Tests

### For Data Engine
Add to `tests/data_engine/test_data_engine.py` or create new files like:
- `test_metadata.py` - Metadata store tests
- `test_storage.py` - Storage manager tests

### For Other Components
```bash
tests/
├── api/
│   ├── test_auth.py
│   └── test_workspace.py
├── services/
│   └── test_backtest_service.py
```

## Test Data

Tests use temporary directories and mocked data to avoid:
- Network calls to Yahoo Finance
- Writing to production data directories
- Dependency on external services