# Data Infrastructure API Guide

> **Infrastructure-level market data API**  
> User-agnostic endpoints for data access, symbol management, and automated refresh operations.

---

## 🏗️ **API Architecture**

### **Infrastructure Level**
- **No user authentication required** - Open access to market data
- **No workspace scoping** - Global resource management
- **Shared across all services** - Foundation for backtesting, analytics, etc.
- **Automatic symbol management** - Tracks S&P 500 + top 20 crypto by default

### **Core Components**
- **Data Refresh**: Download and update market data
- **Symbol Management**: Add/remove tracked symbols  
- **Coverage Monitoring**: Check data availability and quality
- **Scheduled Operations**: Automated refresh for production

---

## 📊 **API Endpoints**

### **Data Refresh Operations**

#### `POST /data/refresh`
Refresh market data for tracked symbols with flexible filtering.

**Request Body:**
- `days_back` (int, 1-365): Days of historical data to refresh (default: 30)
- `interval` (string): Data interval - `1d` or `1h` (default: `1d`)
- `asset_type` (string): Filter by asset type - `stocks`, `crypto`, or `all` (default: `all`)
- `async_mode` (boolean): Run in background (default: `true`)

**Example Requests:**
```http
# Refresh all symbols, last 30 days, background mode
POST /data/refresh
Content-Type: application/json

{
  "days_back": 30,
  "asset_type": "all",
  "async_mode": true
}

# Refresh only stocks, last 7 days, synchronous
POST /data/refresh
Content-Type: application/json

{
  "days_back": 7,
  "asset_type": "stocks",
  "async_mode": false
}

# Refresh crypto only, hourly data
POST /data/refresh
Content-Type: application/json

{
  "asset_type": "crypto",
  "interval": "1h"
}
```

**Response (Async):**
```json
{
  "message": "Data refresh started in background",
  "estimated_duration": "140 seconds",
  "symbols_count": 70,
  "status": "started"
}
```

**Response (Sync):**
```json
{
  "message": "Data refresh completed",
  "result": {
    "success": [
      {
        "symbol": "AAPL",
        "success": true,
        "rows": 126,
        "date_range": "2024-01-01 to 2024-06-30",
        "latest_price": 193.24
      }
    ],
    "failed": [],
    "summary": {
      "total_symbols": 70,
      "successful": 68,
      "failed": 2,
      "success_rate": 97.14
    }
  },
  "status": "completed"
}
```

---

### **Symbol Management**

#### `GET /data/symbols`
Get list of all tracked symbols.

**Query Parameters:**
- `asset_type` (optional): Filter by `stocks` or `crypto`

**Example Requests:**
```http
# Get all symbols
GET /data/symbols

# Get only stocks
GET /data/symbols?asset_type=stocks

# Get only crypto
GET /data/symbols?asset_type=crypto
```

**Response:**
```json
{
  "stocks": [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"
  ],
  "crypto": [
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD"
  ],
  "total": 70
}
```

#### `POST /data/symbols`
Add a symbol to the tracking list.

**Request Body:**
- `symbol` (required): Symbol to add (e.g., `NVDA`, `SOL-USD`)
- `asset_type` (optional): `auto`, `stock`, or `crypto` (default: `auto`)

**Example Requests:**
```http
# Add stock (auto-detected)
POST /data/symbols
Content-Type: application/json

{
  "symbol": "NVDA"
}

# Add crypto explicitly
POST /data/symbols
Content-Type: application/json

{
  "symbol": "SOL-USD",
  "asset_type": "crypto"
}

# Add with explicit type
POST /data/symbols
Content-Type: application/json

{
  "symbol": "TSLA",
  "asset_type": "stock"
}
```

**Response:**
```json
{
  "message": "Symbol NVDA added successfully",
  "symbol": "NVDA",
  "asset_type": "stock"
}
```

#### `DELETE /data/symbols/{symbol}`
Remove a symbol from tracking.

**Path Parameters:**
- `symbol`: Symbol to remove

**Example Requests:**
```http
# Remove stock
DELETE /data/symbols/NVDA

# Remove crypto
DELETE /data/symbols/SOL-USD
```

**Response:**
```json
{
  "message": "Symbol NVDA removed successfully",
  "symbol": "NVDA"
}
```

---

### **Coverage Monitoring**

#### `GET /data/coverage`
Get data coverage summary for tracked symbols.

**Query Parameters:**
- `symbol` (optional): Get coverage for specific symbol only

**Example Requests:**
```http
# Get coverage summary for all symbols
GET /data/coverage

# Get coverage for specific symbol
GET /data/coverage?symbol=AAPL
```

**Response (All Symbols):**
```json
{
  "stocks": {
    "AAPL": {
      "raw": {
        "earliest": "2024-01-01",
        "latest": "2024-06-30", 
        "file_count": 1,
        "total_rows": 126
      },
      "processed": {
        "earliest": "2024-01-01",
        "latest": "2024-06-30",
        "file_count": 1,
        "total_rows": 126
      },
      "cache": {
        "earliest": "2024-03-01",
        "latest": "2024-03-31",
        "file_count": 2,
        "total_rows": 43
      }
    }
  },
  "crypto": {
    "BTC-USD": { /* similar structure */ }
  },
  "total_symbols": 70,
  "coverage_stats": {
    "full_coverage": 65,
    "partial_coverage": 3,
    "no_coverage": 2
  }
}
```

**Response (Single Symbol):**
```json
{
  "symbol": "AAPL",
  "coverage": {
    "raw": {
      "earliest": "2024-01-01",
      "latest": "2024-06-30",
      "file_count": 1,
      "total_rows": 126
    },
    "processed": {
      "earliest": "2024-01-01", 
      "latest": "2024-06-30",
      "file_count": 1,
      "total_rows": 126
    },
    "cache": {
      "earliest": "2024-03-01",
      "latest": "2024-03-31", 
      "file_count": 2,
      "total_rows": 43
    }
  }
}
```

---

### **Scheduled Operations**

#### `POST /data/refresh/daily`
Daily scheduled refresh (last 7 days) - designed for cron jobs.

**Example Request:**
```http
POST /data/refresh/daily
```

**Response:**
```json
{
  "message": "Daily refresh started",
  "schedule": "Last 7 days",
  "status": "started"
}
```

#### `POST /data/refresh/weekly` 
Weekly scheduled refresh (last 30 days) - designed for cron jobs.

**Example Request:**
```http
POST /data/refresh/weekly
```

**Response:**
```json
{
  "message": "Weekly refresh started",
  "schedule": "Last 30 days",
  "status": "started"
}
```

#### `POST /data/refresh/monthly`
Monthly scheduled refresh (last 90 days) - designed for cron jobs.

**Example Request:**
```http
POST /data/refresh/monthly
```

**Response:**
```json
{
  "message": "Monthly refresh started", 
  "schedule": "Last 90 days",
  "status": "started"
}
```

---

## 📋 **Usage Examples**

### **Basic Data Refresh**
```bash
# Refresh all data for last 30 days
curl -X POST "http://localhost:8000/data/refresh?days_back=30"

# Refresh only stocks synchronously
curl -X POST "http://localhost:8000/data/refresh?asset_type=stocks&async_mode=false"
```

### **Symbol Management Workflow**
```bash
# Check current symbols
curl "http://localhost:8000/data/symbols"

# Add new symbol
curl -X POST "http://localhost:8000/data/symbols?symbol=NVDA"

# Remove symbol
curl -X DELETE "http://localhost:8000/data/symbols/NVDA"

# Check stocks only
curl "http://localhost:8000/data/symbols?asset_type=stocks"
```

### **Coverage Monitoring**
```bash
# Check overall coverage
curl "http://localhost:8000/data/coverage"

# Check specific symbol coverage
curl "http://localhost:8000/data/coverage?symbol=AAPL"
```

### **Automation Setup**
```bash
# Daily cron job (run at 6 AM)
0 6 * * * curl -X POST "http://localhost:8000/data/refresh/daily"

# Weekly cron job (run Sunday at 2 AM)  
0 2 * * 0 curl -X POST "http://localhost:8000/data/refresh/weekly"

# Monthly cron job (run 1st of month at 1 AM)
0 1 1 * * curl -X POST "http://localhost:8000/data/refresh/monthly"
```

---

## 🎯 **Integration Patterns**

### **Service Layer Integration**
```python
# Other services can use DataService directly
from services.data_service import DataService

class BacktestService:
    def __init__(self):
        self.data_service = DataService()
    
    async def run_backtest(self, symbols, start_date, end_date):
        # Ensure data is available
        await self.data_service.refresh_all_symbols(days_back=30)
        
        # Access data engine directly for performance
        from core.data_engine import DataEngine
        engine = DataEngine()
        data = engine.get_data(symbols[0], start_date, end_date)
        
        # Run backtest logic...
```

### **Frontend Integration**
```javascript
// Check data availability before backtesting
const coverage = await fetch('/data/coverage').then(r => r.json());

// Trigger refresh if needed
if (coverage.coverage_stats.no_coverage > 0) {
  await fetch('/data/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ days_back: 30 })
  });
}

// Get available symbols for dropdowns
const symbols = await fetch('/data/symbols').then(r => r.json());
```

### **External Tool Integration**
```python
import requests

# Python script to sync external data
def sync_portfolio_data(portfolio_symbols):
    # Add portfolio symbols to tracking
    for symbol in portfolio_symbols:
        requests.post("http://api/data/symbols", json={"symbol": symbol})
    
    # Refresh data
    response = requests.post("http://api/data/refresh", json={
        "days_back": 90,
        "async_mode": False
    })
    return response.json()
```

---

## 🔧 **Error Handling**

### **Common Error Responses**

#### **400 Bad Request**
```json
{
  "detail": "Invalid symbol format: INVALID_SYMBOL"
}
```

#### **500 Internal Server Error**  
```json
{
  "detail": "Data refresh failed: Network timeout"
}
```

### **Handling Async Operations**
```python
# Check if async operation is still running
response = requests.post("/data/refresh", params={"async_mode": True})
if response.json()["status"] == "started":
    # Poll coverage endpoint to check progress
    while True:
        coverage = requests.get("/data/coverage").json()
        if coverage["coverage_stats"]["full_coverage"] > expected_count:
            break
        time.sleep(30)
```

---

## 🚀 **Performance Notes**

### **Optimization Tips**
- **Use async mode** for large refresh operations (>10 symbols)
- **Filter by asset_type** to reduce refresh time
- **Monitor coverage** before triggering unnecessary refreshes
- **Use scheduled endpoints** for automation instead of manual triggers

### **Rate Limiting**
- **Data provider limits**: Yahoo Finance has rate limits (~2000 requests/hour)
- **Concurrent downloads**: Limited to 5 parallel downloads
- **Background processing**: All async operations run in thread pool

### **Caching Strategy**
- **Smart caching**: 2nd calls to same date range are instant
- **4-layer architecture**: Raw → Processed → Cache → Metadata
- **Automatic cleanup**: Old cache files are managed automatically

---

## 🔒 **Security Considerations**

### **No Authentication Required**
- **Infrastructure-level**: Designed for internal services
- **Open access**: Market data is not sensitive
- **Rate limiting**: Prevent abuse through request throttling

### **Production Deployment**
- **Internal network**: Deploy behind firewall
- **Service mesh**: Use internal service communication
- **Monitoring**: Log all refresh operations for audit

---

**This API provides the foundation for all market data operations across your quantitative platform.**