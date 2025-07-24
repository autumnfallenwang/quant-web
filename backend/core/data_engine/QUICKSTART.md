# core/data_engine/QUICKSTART.md

# Data Engine Quick Start

## 30-Second Test

```python
from core.data_engine import DataEngine
from datetime import date

# Initialize and get data
engine = DataEngine()
data = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))

print(f"Got {len(data)} rows")
print(f"Latest close: ${data['Close'].iloc[-1]:.2f}")
```

## What You Get

✅ **Professional 4-layer architecture**  
✅ **Automatic caching** - 2nd calls are instant  
✅ **Clean API** - Just `get_data(symbol, start, end)`  
✅ **Scalable storage** - Room for entire market history  
✅ **Complete test suite** - `pytest tests/`  

## File Structure Created

```
/home/aaronwang/quant-data/
├── raw/          # Original Yahoo Finance downloads
├── processed/    # Split/dividend adjusted data
├── cache/        # Query results for fast access  
└── metadata/     # SQLite database tracking
```

## Run Tests

```bash
# Simple manual test
python tests/simple_test.py

# Full data engine test suite (17 tests)
python -m pytest tests/data_engine/ -v

# Basic functionality only (5 tests)
python -m pytest tests/data_engine/test_data_engine.py::TestBasicFunctionality -v

# All backend tests
pytest
```

## Ready for Backtesting! 🚀

The data engine is now a self-contained, production-ready component that can power serious quantitative backtesting strategies.