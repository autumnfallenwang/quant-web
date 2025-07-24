# core/data_engine/README.md

# Data Engine Documentation

Professional 4-layer market data engine for quantitative backtesting platform.

## Architecture

```
📁 Data Engine Structure:
├── raw/          # Immutable original downloads
├── processed/    # Split/dividend adjusted data  
├── cache/        # Query-specific results
└── metadata/     # SQLite database tracking
```

## Quick Start

```python
from core.data_engine import DataEngine
from datetime import date

# Initialize engine
engine = DataEngine()

# Get market data
data = engine.get_data(
    symbol='AAPL',
    start=date(2024, 1, 1),
    end=date(2024, 6, 30),
    interval='1d'
)

print(f"Got {len(data)} rows of data")
print(data.head())
```

## API Reference

### Core Methods

#### `get_data(symbol, start, end, interval='1d')`

Get market data for a symbol within date range.

**Parameters:**
- `symbol` (str): Stock or crypto symbol
  - Stocks: `'AAPL'`, `'GOOGL'`, `'MSFT'`
  - Crypto: `'BTC-USD'`, `'ETH-USD'`
- `start` (date): Start date (inclusive)
- `end` (date): End date (inclusive)
- `interval` (str): Data interval
  - `'1d'`: Daily data (default)
  - `'1h'`: Hourly data

**Returns:**
- `pd.DataFrame`: OHLCV data with DatetimeIndex

**Example:**
```python
from datetime import date

# Get Apple stock data for Q1 2024
data = engine.get_data('AAPL', date(2024, 1, 1), date(2024, 3, 31))

# Data columns:
# - Open, High, Low, Close, Volume
# - Dividends, Stock Splits  
# - Adj_Close (split/dividend adjusted)
```

#### `get_symbols(asset_type=None)`

Get list of available symbols.

**Parameters:**
- `asset_type` (str, optional): Filter by asset type
  - `'stock'`: Stock symbols only
  - `'crypto'`: Crypto symbols only
  - `None`: All symbols (default)

**Returns:**
- `list`: List of symbol strings

**Example:**
```python
# Get all symbols
all_symbols = engine.get_symbols()

# Get only stocks
stocks = engine.get_symbols('stock')

# Get only crypto
crypto = engine.get_symbols('crypto')
```

#### `get_data_coverage(symbol, interval='1d')`

Get data coverage information for a symbol.

**Parameters:**
- `symbol` (str): Symbol to check
- `interval` (str): Data interval

**Returns:**
- `dict`: Coverage information by data type

**Example:**
```python
coverage = engine.get_data_coverage('AAPL', '1d')

# Returns:
# {
#   'raw': {'earliest': '2024-01-01', 'latest': '2024-06-30', 'file_count': 1, 'total_rows': 126},
#   'processed': {'earliest': '2024-01-01', 'latest': '2024-06-30', 'file_count': 1, 'total_rows': 126},
#   'cache': {'earliest': '2024-03-01', 'latest': '2024-03-31', 'file_count': 2, 'total_rows': 43}
# }
```

## Usage Examples

### Basic Stock Data

```python
from core.data_engine import DataEngine
from datetime import date

engine = DataEngine()

# Get recent Apple data
apple_data = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))

print(f"Apple June 2024:")
print(f"Rows: {len(apple_data)}")
print(f"Price range: ${apple_data['Low'].min():.2f} - ${apple_data['High'].max():.2f}")
print(f"Latest close: ${apple_data['Close'].iloc[-1]:.2f}")
```

### Crypto Data

```python
# Get Bitcoin data
btc_data = engine.get_data('BTC-USD', date(2024, 7, 1), date(2024, 7, 15))

print(f"Bitcoin July 2024:")
print(f"Rows: {len(btc_data)}")
print(f"Latest price: ${btc_data['Close'].iloc[-1]:,.2f}")
```

### Multiple Symbols

```python
# Get data for multiple symbols
symbols = ['AAPL', 'GOOGL', 'MSFT', 'BTC-USD', 'ETH-USD']
start_date = date(2024, 6, 1)
end_date = date(2024, 6, 30)

portfolio_data = {}
for symbol in symbols:
    data = engine.get_data(symbol, start_date, end_date)
    if not data.empty:
        portfolio_data[symbol] = data
        print(f"{symbol}: {len(data)} rows, latest: ${data['Close'].iloc[-1]:.2f}")
```

### Hourly Data

```python
# Get hourly data for day trading strategies
hourly_data = engine.get_data('AAPL', date(2024, 7, 20), date(2024, 7, 22), '1h')

print(f"AAPL hourly data:")
print(f"Rows: {len(hourly_data)}")
print(f"Trading hours covered: {hourly_data.index.min()} to {hourly_data.index.max()}")
```

### Data Analysis

```python
# Analyze data quality
data = engine.get_data('AAPL', date(2024, 1, 1), date(2024, 6, 30))

print("Data Quality Check:")
print(f"Missing values: {data.isnull().sum().sum()}")
print(f"Date range: {data.index.min().date()} to {data.index.max().date()}")
print(f"Trading days: {len(data)}")

# Check for stock splits/dividends
splits = data[data['Stock Splits'] > 0]
dividends = data[data['Dividends'] > 0]

print(f"Stock splits: {len(splits)}")
print(f"Dividends: {len(dividends)}")
if len(dividends) > 0:
    print(f"Total dividends: ${dividends['Dividends'].sum():.2f}")
```

## Performance Features

### Automatic Caching

The engine automatically caches results for faster subsequent queries:

```python
import time

# First call - downloads and processes data
start_time = time.time()
data1 = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))
first_call_time = time.time() - start_time

# Second call - uses cache
start_time = time.time()
data2 = engine.get_data('AAPL', date(2024, 6, 1), date(2024, 6, 30))  
second_call_time = time.time() - start_time

print(f"First call (download): {first_call_time:.2f}s")
print(f"Second call (cache): {second_call_time:.2f}s")
print(f"Speedup: {first_call_time/second_call_time:.1f}x")
```

### Data Integrity

All data is stored in multiple layers with full audit trail:

```python
# Check data coverage
coverage = engine.get_data_coverage('AAPL', '1d')
print("Data layers:", list(coverage.keys()))

# Verify data consistency
symbols = engine.get_symbols()
print(f"Available symbols: {len(symbols)}")
```

## File Structure

The engine creates this directory structure:

```
${DATA_ENGINE_ROOT}/
├── raw/
│   ├── stocks/daily/AAPL_2024.parquet        # Original Yahoo Finance data
│   └── crypto/daily/BTC_USD_2024.parquet
├── processed/
│   ├── stocks/daily/AAPL_2024.parquet        # Split/dividend adjusted
│   └── crypto/daily/BTC_USD_2024.parquet  
├── cache/
│   ├── stocks/daily/AAPL_2024-06-01_2024-06-30.parquet  # Query results
│   └── crypto/daily/BTC_USD_2024-07-01_2024-07-15.parquet
└── metadata/
    └── symbols.db                             # SQLite metadata database
```

## Configuration

The engine uses the `DATA_ENGINE_ROOT` setting from your `.env` file:

```bash
# backend/.env
DATA_ENGINE_ROOT="/path/to/your/data/storage"
```

## Error Handling

The engine gracefully handles common issues:

```python
# Invalid symbol
data = engine.get_data('INVALID', date(2024, 1, 1), date(2024, 1, 31))
print(f"Invalid symbol returns empty DataFrame: {data.empty}")

# Future dates
data = engine.get_data('AAPL', date(2025, 1, 1), date(2025, 1, 31))
print(f"Future dates return empty DataFrame: {data.empty}")

# Weekends/holidays are handled automatically
data = engine.get_data('AAPL', date(2024, 7, 6), date(2024, 7, 8))  # Weekend
print(f"Weekend query: {len(data)} rows")  # Returns available trading days
```

## Best Practices

1. **Use daily data** for most backtesting strategies
2. **Cache frequently used date ranges** by running queries once
3. **Check data coverage** before running long backtests
4. **Handle empty DataFrames** in your strategies
5. **Use appropriate date ranges** - avoid requesting future data

## Integration Example

```python
# Example: Simple backtesting integration
from core.data_engine import DataEngine
from datetime import date

def simple_moving_average_strategy(symbol, start_date, end_date, window=20):
    engine = DataEngine()
    
    # Get data
    data = engine.get_data(symbol, start_date, end_date)
    if data.empty:
        return None
    
    # Calculate moving average
    data['SMA'] = data['Close'].rolling(window=window).mean()
    
    # Generate signals
    data['Signal'] = 0
    data.loc[data['Close'] > data['SMA'], 'Signal'] = 1
    data.loc[data['Close'] < data['SMA'], 'Signal'] = -1
    
    return data

# Run strategy
result = simple_moving_average_strategy('AAPL', date(2024, 1, 1), date(2024, 6, 30))
if result is not None:
    print(f"Strategy generated {len(result)} signals")
```