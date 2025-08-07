# Backtesting API Documentation

Complete reference for the Backtesting Engine REST API following workspace-scoped patterns.

## 📋 Overview

The Backtesting API provides comprehensive backtesting capabilities for quantitative trading strategies. It enables users to:
- Create and manage backtests within workspaces
- Execute strategy backtests against historical market data  
- Analyze backtest performance and risk metrics
- Track backtest execution status and results
- Manage workspace-level backtest analytics

## 🏗️ Architecture

The Backtesting Engine follows the established four-layer architecture:

```
┌─────────────────────────────────────────┐
│ API Layer (backtesting.py)             │
│ • REST endpoints                        │
│ • Request/response validation           │
│ • Authentication & authorization        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ Service Layer (backtesting_service.py) │
│ • Business logic                        │
│ • Data/Strategy service integration     │
│ • Job orchestration                     │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ Core Engine (core/backtesting_engine/)  │
│ • Portfolio simulation                  │
│ • Execution engine                      │
│ • Performance metrics calculation       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ Database Models (db_models.py)         │
│ • Backtest, BacktestTrade              │
│ • BacktestDailyMetric, BacktestPosition │
└─────────────────────────────────────────┘
```

## 🚀 Quick Start

### Authentication
All endpoints require Bearer token authentication:
```bash
Authorization: Bearer <your_access_token>
```

### Base URL
```
http://localhost:8000
```

### Create Your First Backtest
```bash
# 1. Create a backtest
POST /workspace/1/backtests
{
  "name": "My First Backtest",
  "strategy_id": 1,
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "initial_capital": 100000.0,
  "symbols": ["AAPL", "MSFT", "GOOGL"]
}

# 2. Start execution
POST /workspace/1/backtests/1/start

# 3. Check results
GET /workspace/1/backtests/1/results
```

## 📚 API Reference

### 🏢 Workspace Backtest Collection

#### List Backtests
```http
GET /workspace/{workspace_id}/backtests
```

**Parameters:**
- `workspace_id` (path, required): Workspace ID
- `strategy_id` (query, optional): Filter by strategy ID  
- `status` (query, optional): Filter by status (`created`, `running`, `completed`, `failed`, `cancelled`)
- `sort` (query, optional): Sort field (`name`, `created_at`, `status`)
- `order` (query, optional): Sort order (`asc`, `desc`). Default: `desc`
- `page` (query, optional): Page number (≥1). Default: 1
- `limit` (query, optional): Items per page (1-100). Default: 50

**Response:**
```json
{
  "backtests": [
    {
      "id": 1,
      "backtest_id": "bt_abc123",
      "name": "Momentum Strategy Test",
      "strategy_id": 1,
      "status": "completed",
      "start_date": "2024-01-01T00:00:00Z",
      "end_date": "2024-01-31T23:59:59Z",
      "initial_capital": 100000.0,
      "symbols": ["AAPL", "MSFT", "GOOGL"],
      "return_percentage": 15.2,
      "sharpe_ratio": 1.4,
      "max_drawdown": -8.5,
      "created_at": "2024-02-01T10:00:00Z",
      "updated_at": "2024-02-01T10:30:00Z"
    }
  ],
  "total_count": 10,
  "page": 1,
  "page_size": 50
}
```

#### Create Backtest
```http
POST /workspace/{workspace_id}/backtests
```

**Request Body:**
```json
{
  "name": "My Backtest",
  "strategy_id": 1,
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z", 
  "initial_capital": 100000.0,
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "description": "Testing momentum strategy",
  "commission_per_share": 0.01,
  "commission_percentage": null,
  "slippage": 0.001
}
```

**Response (201):**
```json
{
  "id": 1,
  "backtest_id": "bt_abc123",
  "name": "My Backtest",
  "strategy_id": 1,
  "status": "created",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "initial_capital": 100000.0,
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "description": "Testing momentum strategy",
  "commission_per_share": 0.01,
  "commission_percentage": null,
  "slippage": 0.001,
  "created_at": "2024-02-01T10:00:00Z",
  "updated_at": "2024-02-01T10:00:00Z"
}
```

### 🎯 Individual Backtest Operations

#### Get Backtest Details
```http
GET /workspace/{workspace_id}/backtests/{backtest_id}
```

**Response:**
```json
{
  "id": 1,
  "backtest_id": "bt_abc123",
  "name": "My Backtest",
  "strategy_id": 1,
  "status": "completed",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "initial_capital": 100000.0,
  "final_capital": 115200.0,
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "return_percentage": 15.2,
  "sharpe_ratio": 1.4,
  "max_drawdown": -8.5,
  "total_trades": 45,
  "winning_trades": 28,
  "losing_trades": 17,
  "created_at": "2024-02-01T10:00:00Z",
  "updated_at": "2024-02-01T10:30:00Z"
}
```

#### Start Backtest Execution
```http
POST /workspace/{workspace_id}/backtests/{backtest_id}/start
```

**Response:**
```json
{
  "job_id": "job_xyz789",
  "backtest_id": 1,
  "status": "running",
  "message": "Backtest execution started",
  "progress_percent": 0,
  "estimated_duration": 600,
  "created_at": "2024-02-01T10:00:00Z"
}
```

#### Cancel Backtest
```http
POST /workspace/{workspace_id}/backtests/{backtest_id}/cancel
```

**Response:**
```json
{
  "message": "Backtest cancelled successfully",
  "backtest_id": 1
}
```

**Error Response (400):**
```json
{
  "detail": "Backtest cannot be cancelled (not running)"
}
```

#### Get Backtest Results
```http
GET /workspace/{workspace_id}/backtests/{backtest_id}/results
```

**Response (200 - Completed):**
```json
{
  "backtest_id": "bt_abc123",
  "status": "completed",
  "execution_time": 245.5,
  "total_return": 15200.0,
  "return_percentage": 15.2,
  "annualized_return": 18.5,
  "sharpe_ratio": 1.4,
  "max_drawdown": -8.5,
  "volatility": 12.8,
  "total_trades": 45,
  "winning_trades": 28,
  "losing_trades": 17,
  "win_rate": 62.2,
  "daily_metrics": [
    {
      "date": "2024-01-01",
      "portfolio_value": 102500.0,
      "daily_return": 2.5,
      "cumulative_return": 2.5
    }
  ],
  "trades": [
    {
      "symbol": "AAPL",
      "trade_type": "buy",
      "quantity": 100,
      "price": 150.0,
      "total_amount": 15000.0,
      "commission": 1.0,
      "executed_at": "2024-01-02T09:30:00Z"
    }
  ],
  "positions": [
    {
      "symbol": "AAPL", 
      "quantity": 100,
      "average_price": 150.0,
      "current_price": 165.0,
      "market_value": 16500.0,
      "unrealized_pnl": 1500.0
    }
  ]
}
```

**Response (202 - Still Running):**
```json
{
  "status": "running", 
  "message": "Backtest is running",
  "backtest_id": "bt_abc123"
}
```

### 🔧 Backtest Management

#### Update Backtest
```http
PATCH /workspace/{workspace_id}/backtests/{backtest_id}
```

**Request Body:**
```json
{
  "name": "Updated Backtest Name",
  "description": "Updated description"
}
```

**Note:** Only `name` and `description` can be updated. Cannot update running backtests.

#### Delete Backtest
```http
DELETE /workspace/{workspace_id}/backtests/{backtest_id}
```

**Response:**
```json
{
  "message": "Backtest deleted successfully",
  "backtest_id": 1
}
```

**Note:** Cannot delete running backtests.

### 📊 Workspace Analytics

#### Get Backtest Analytics
```http
GET /workspace/{workspace_id}/backtest-analytics
```

**Response:**
```json
{
  "total_backtests": 25,
  "completed_backtests": 20,
  "running_backtests": 2,
  "failed_backtests": 3,
  "avg_return_percentage": 12.5,
  "avg_sharpe_ratio": 1.2,
  "avg_max_drawdown": -7.8,
  "best_performing_backtest": {
    "id": 15,
    "name": "High Momentum Strategy",
    "return_percentage": 45.2
  },
  "worst_performing_backtest": {
    "id": 8,
    "name": "Conservative Strategy", 
    "return_percentage": -3.1
  }
}
```

## 🔐 Authentication & Authorization

### Required Headers
```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Access Control
- Users can only access backtests they created
- Workspace access is validated for all operations
- Strategy access is checked during backtest creation

## ❌ Error Responses

### 400 Bad Request
```json
{
  "detail": "Strategy not found or not accessible"
}
```

### 401 Unauthorized  
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to access this workspace"  
}
```

### 404 Not Found
```json
{
  "detail": "Backtest not found in specified workspace"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "initial_capital"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to create backtest: Database connection error"
}
```

## 📋 Status Values

### Backtest Status
- `created` - Backtest created but not started
- `running` - Currently executing
- `completed` - Successfully finished
- `failed` - Execution failed
- `cancelled` - Cancelled by user

### Trade Types
- `buy` - Long position entry
- `sell` - Long position exit or short position entry
- `short` - Short position entry
- `cover` - Short position exit

## 🎯 Collection Analytics Pattern

The API uses the **Collection Analytics Pattern** to avoid route conflicts:

✅ **Correct:**
```http
GET /workspace/{id}/backtests/{backtest_id}  # Individual resource
GET /workspace/{id}/backtest-analytics       # Collection analytics
```

❌ **Incorrect:**
```http
GET /workspace/{id}/backtests/{backtest_id}  # Individual resource  
GET /workspace/{id}/backtests/summary        # Conflicts with {backtest_id}
```

This pattern provides:
- Clear semantic separation between resources and analytics
- No routing conflicts with resource IDs
- Extensible for different analytics types
- Consistent with established API design patterns

## 🔍 Examples

### Complete Backtest Workflow
```python
import requests

base_url = "http://localhost:8000"
headers = {"Authorization": "Bearer your_token"}

# 1. Create backtest
backtest_data = {
    "name": "MACD Strategy Test",
    "strategy_id": 1,
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-03-31T23:59:59Z",
    "initial_capital": 100000.0,
    "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN"],
    "commission_per_share": 0.01,
    "slippage": 0.001
}

response = requests.post(
    f"{base_url}/workspace/1/backtests",
    json=backtest_data,
    headers=headers
)
backtest = response.json()
backtest_id = backtest["id"]

# 2. Start execution
response = requests.post(
    f"{base_url}/workspace/1/backtests/{backtest_id}/start",
    headers=headers
)
job = response.json()
print(f"Started job: {job['job_id']}")

# 3. Poll for completion
import time
while True:
    response = requests.get(
        f"{base_url}/workspace/1/backtests/{backtest_id}/results",
        headers=headers
    )
    
    if response.status_code == 200:
        results = response.json()
        print(f"Backtest completed! Return: {results['return_percentage']:.1f}%")
        break
    elif response.status_code == 202:
        print("Still running...")
        time.sleep(10)
    else:
        print("Error occurred")
        break

# 4. Get workspace analytics
response = requests.get(
    f"{base_url}/workspace/1/backtest-analytics",
    headers=headers
)
analytics = response.json()
print(f"Workspace has {analytics['total_backtests']} total backtests")
```

### Filtering and Pagination
```python
# Get completed backtests, sorted by return percentage
params = {
    "status": "completed",
    "sort": "return_percentage", 
    "order": "desc",
    "page": 1,
    "limit": 20
}

response = requests.get(
    f"{base_url}/workspace/1/backtests",
    params=params,
    headers=headers
)

backtests = response.json()
for bt in backtests["backtests"]:
    print(f"{bt['name']}: {bt['return_percentage']:.1f}%")
```

## 🧪 Testing

The API includes comprehensive real HTTP tests in `tests/backtesting_engine/test_backtesting_api_real_http.py`.

Run tests:
```bash
# Start the server
uvicorn main:app --reload --port 8000

# Run tests
python tests/backtesting_engine/test_backtesting_api_real_http.py
```

Expected output:
```
🚀 BACKTESTING API REAL HTTP TESTS
Testing complete Backtesting Engine via HTTP API
============================================================

🧪 Test 1: Authentication
✅ Authentication successful

🧪 Test 2: Create Strategy for Backtesting  
✅ Strategy created: ID=1, Name='Backtest Strategy 1234567890'

🧪 Test 3: Create Backtest
✅ Backtest created: ID=1, Name='Test Backtest 1234567890'

...

📊 TEST RESULTS
============================================================
✅ PASSED: 9
❌ FAILED: 1  
📈 SUCCESS RATE: 90.0%
```

## 🏗️ Implementation Notes

### Database Models
- `Backtest`: Main backtest configuration and results
- `BacktestTrade`: Individual trade records
- `BacktestDailyMetric`: Daily performance snapshots
- `BacktestPosition`: Position snapshots over time

### Service Integration
- **DataService**: Fetches historical market data
- **StrategyService**: Provides strategy logic and parameters
- **JobService**: Manages background execution

### Performance Considerations
- Backtests run as background jobs
- Results are cached in the database
- Large datasets are paginated
- API responses are optimized for client consumption

### Validation Rules
- `end_date` must be after `start_date`
- `initial_capital` must be positive
- Strategy must exist and be accessible
- Workspace access is validated
- Symbol list cannot be empty

This comprehensive API enables full backtesting capabilities with robust error handling, authentication, and performance optimization.