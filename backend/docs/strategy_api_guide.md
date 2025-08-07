# Strategy Engine API Guide

## Overview

The Strategy Engine API provides comprehensive endpoints for managing trading strategies within workspaces with **real market data integration via DataService**. All endpoints are workspace-scoped and require authentication.

**✅ NEW**: Strategy Engine now uses **DataService** for real market data analysis and signal generation  
**🔄 CHANGED**: Backtesting has been moved to a **separate Backtesting Engine** for better modularity

**Base Path**: `/api/v1`
**Authentication**: Bearer token required for all endpoints

## Strategy Types

- `momentum`: Momentum-based trading strategies
- `mean_reversion`: Mean reversion strategies using statistical indicators
- `arbitrage`: Arbitrage opportunity detection strategies
- `custom`: Custom user-defined strategies

## Risk Levels

- `low`: Conservative risk profile
- `medium`: Balanced risk profile  
- `high`: Aggressive risk profile

---

## Strategy Management

### 1. List Strategies

Get a paginated list of strategies in a workspace with filtering and sorting.

**Endpoint**: `GET /workspace/{workspace_id}/strategies`

**Parameters**:
- `workspace_id` (path, required): Workspace ID
- `strategy_type` (query, optional): Filter by strategy type
- `is_active` (query, optional): Filter by active status
- `sort` (query, optional): Sort field (name, created_at, updated_at)
- `order` (query, optional): Sort order (asc/desc, default: desc)
- `page` (query, optional): Page number (default: 1)
- `limit` (query, optional): Items per page (default: 50, max: 100)

**Response**:
```json
{
  "strategies": [
    {
      "id": 1,
      "name": "Momentum Strategy",
      "description": "A momentum-based trading strategy",
      "strategy_type": "momentum",
      "strategy_code": null,
      "is_active": true,
      "is_public": false,
      "risk_level": "medium",
      "workspace_id": 1,
      "created_by": 1,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "parameter_count": 3
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 50
}
```

**Example**:
```bash
curl -X GET "/workspace/1/strategies?strategy_type=momentum&page=1&limit=10" \
  -H "Authorization: Bearer <token>"
```

---

### 2. Create Strategy

Create a new trading strategy in a workspace.

**Endpoint**: `POST /workspace/{workspace_id}/strategies`

**Parameters**:
- `workspace_id` (path, required): Workspace ID

**Request Body**:
```json
{
  "name": "My Momentum Strategy",
  "strategy_type": "momentum",
  "description": "A custom momentum strategy",
  "strategy_code": null,
  "risk_level": "medium",
  "is_public": false,
  "parameters": [
    {
      "name": "lookback_period",
      "type": "int",
      "default_value": "20",
      "current_value": "20",
      "min_value": "1",
      "max_value": "100",
      "description": "Period for momentum calculation",
      "is_required": true
    }
  ]
}
```

**Response**: Returns a `StrategyResponse` object (same as list item above)

**Status Code**: `201 Created`

**Example**:
```bash
curl -X POST "/workspace/1/strategies" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Strategy",
    "strategy_type": "momentum",
    "risk_level": "medium"
  }'
```

---

### 3. Get Strategy

Retrieve details of a specific strategy.

**Endpoint**: `GET /workspace/{workspace_id}/strategies/{strategy_id}`

**Parameters**:
- `workspace_id` (path, required): Workspace ID
- `strategy_id` (path, required): Strategy ID

**Response**: Returns a `StrategyResponse` object

**Example**:
```bash
curl -X GET "/workspace/1/strategies/123" \
  -H "Authorization: Bearer <token>"
```

---

### 4. Update Strategy

Update strategy details.

**Endpoint**: `PATCH /workspace/{workspace_id}/strategies/{strategy_id}`

**Parameters**:
- `workspace_id` (path, required): Workspace ID
- `strategy_id` (path, required): Strategy ID

**Request Body**:
```json
{
  "name": "Updated Strategy Name",
  "description": "Updated description",
  "strategy_code": "// Updated code",
  "risk_level": "high",
  "is_active": true
}
```

**Response**: Returns updated `StrategyResponse` object

**Example**:
```bash
curl -X PATCH "/workspace/1/strategies/123" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name", "risk_level": "high"}'
```

---

## Strategy Parameters

### 5. Get Strategy Parameters

Retrieve all parameters for a strategy.

**Endpoint**: `GET /workspace/{workspace_id}/strategies/{strategy_id}/parameters`

**Response**:
```json
[
  {
    "id": 1,
    "strategy_id": 123,
    "parameter_name": "lookback_period",
    "parameter_type": "int",
    "default_value": "20",
    "current_value": "25",
    "min_value": "1",
    "max_value": "100",
    "description": "Period for momentum calculation",
    "is_required": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### 6. Update Strategy Parameter

Update a specific parameter value.

**Endpoint**: `PATCH /workspace/{workspace_id}/strategies/{strategy_id}/parameters/{parameter_name}`

**Parameters**:
- `parameter_name` (path, required): Name of the parameter to update

**Request Body**:
```json
{
  "current_value": "30"
}
```

**Response**: Returns updated parameter object

---

## Strategy Analysis

### 7. Analyze Strategy (🆕 With Real Market Data)

Perform quick or comprehensive analysis of a strategy using **real market data from DataService**.

**Endpoint**: `POST /workspace/{workspace_id}/strategies/{strategy_id}/analyze`

**Request Body**:
```json
{
  "analysis_type": "quick",
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "include_risk_metrics": true,
  "include_allocation": true
}
```

**Request Body Parameters**:
- `analysis_type` (required): "quick" or "comprehensive"
- `symbols` (optional): List of symbols to analyze (default: top 5 stocks, max: 50)
- `include_risk_metrics` (optional): Include risk analysis (default: true)
- `include_allocation` (optional): Include allocation analysis (default: true)

**Example**:
```bash
curl -X POST "/workspace/1/strategies/123/analyze" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "quick",
    "symbols": ["AAPL", "MSFT", "GOOGL"]
  }'
```

**Response for Quick Analysis** (🆕 With Real Market Data):
```json
{
  "strategy_id": 123,
  "performance_metrics": {
    "signals_generated": 5,
    "symbols_analyzed": 3,
    "market_data_availability": 100.0,
    "strategy_complexity_score": 2,
    "avg_signal_confidence": 0.75,
    "data_coverage_days": 30,
    "market_context": {
      "AAPL": {
        "data_points": 30,
        "price_range": {"min": 150.0, "max": 160.0, "current": 155.0},
        "volatility": 0.12
      }
    }
  },
  "risk_metrics": {
    "risk_score": 0.6,
    "parameter_complexity": "medium"
  },
  "signal_analysis": {
    "total_signals": 5,
    "signal_frequency": "medium",
    "signal_types": {"buy": 2, "sell": 1, "hold": 2},
    "symbols_with_signals": ["AAPL", "MSFT"],
    "generators_used": ["momentum"]
  },
  "recommendations": [
    "Strategy appears well-configured - continue monitoring with real market data",
    "Consider diversifying signal sources"
  ],
  "analysis_timestamp": "2024-01-01T00:00:00Z",
  "symbols_analyzed": ["AAPL", "MSFT", "GOOGL"]
}
```

**Response for Comprehensive Analysis**:
```json
{
  "strategy_id": 123,
  "analysis_type": "comprehensive",
  "analysis_timestamp": "2024-01-01T00:00:00Z",
  "job_id": "analysis_job_456",
  "total_value": 0,
  "cash_balance": 0,
  "positions_value": 0
}
```

---

### 8. Backtest Strategy (🔄 DEPRECATED - Moved to Backtesting Engine)

Backtesting functionality has been moved to a **separate Backtesting Engine** for better modularity.

**Endpoint**: `POST /workspace/{workspace_id}/strategies/{strategy_id}/backtest`

**Status**: **DEPRECATED** - Returns 501 Not Implemented

**Response** (Deprecation Notice):
```json
{
  "detail": {
    "error": "Backtesting has been moved to a separate Backtesting Engine",
    "message": "Please use the Backtesting Engine API endpoints for backtesting functionality",
    "migration_info": {
      "old_endpoint": "/workspace/1/strategies/123/backtest",
      "new_endpoint": "/workspace/1/backtests",
      "documentation": "See Backtesting Engine API documentation"
    }
  }
}
```

**Migration Guide**:
- **Old**: `POST /workspace/{id}/strategies/{id}/backtest`
- **New**: `POST /workspace/{id}/backtests` (use Backtesting Engine API)
- **Documentation**: Refer to separate Backtesting Engine API guide

---

## Signal Management

### 9. Generate Signals (🆕 With Real Market Data from DataService)

Generate trading signals using the strategy with **real market data from DataService**.

**Endpoint**: `POST /workspace/{workspace_id}/strategies/{strategy_id}/signals/generate`

**Request Body**:
```json
{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "lookback_days": 30
}
```

**Request Body Parameters**:
- `symbols` (required): List of symbols to generate signals for (min: 1, max: 50)
- `lookback_days` (optional): Days of historical data to use (default: 30, range: 1-365)

**Example**:
```bash
curl -X POST "/workspace/1/strategies/123/signals/generate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "MSFT"],
    "lookback_days": 30
  }'
```

**Response**:
```json
{
  "signals": [
    {
      "signal_type": "buy",
      "symbol": "AAPL",
      "signal_strength": 0.8,
      "price": 155.50,
      "confidence_score": 0.75,
      "created_at": "2024-01-01T12:30:45Z",
      "generator": "momentum"
    },
    {
      "signal_type": "sell",
      "symbol": "MSFT",
      "signal_strength": 0.6,
      "price": 387.20,
      "confidence_score": 0.65,
      "created_at": "2024-01-01T12:30:45Z",
      "generator": "momentum"
    }
  ],
  "total_count": 2
}
```

**Features**:
- ✅ **Real Market Data**: Automatically fetches live market data via DataService
- ✅ **Data Validation**: Ensures data availability before signal generation
- ✅ **Multiple Symbols**: Generate signals for multiple symbols in one request
- ✅ **Historical Context**: Uses configurable lookback period for analysis
- ✅ **Database Storage**: Generated signals are stored and can be retrieved later

---

### 10. Get Signals

Retrieve signals generated by the strategy.

**Endpoint**: `GET /workspace/{workspace_id}/strategies/{strategy_id}/signals`

**Parameters**:
- `signal_type` (query, optional): Filter by signal type (buy/sell/hold/arbitrage)
- `symbol` (query, optional): Filter by trading symbol
- `limit` (query, optional): Number of signals to return (default: 50, max: 100)

**Response**:
```json
{
  "signals": [
    {
      "id": 1,
      "strategy_id": 123,
      "signal_type": "buy",
      "symbol": "AAPL",
      "signal_strength": 0.85,
      "price": 155.50,
      "confidence_score": 0.92,
      "signal_data": {
        "momentum_score": 12.5,
        "rsi": 65.0
      },
      "is_executed": false,
      "executed_at": null,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total_count": 1
}
```

---

## Performance Tracking

### 11. Get Strategy Performance

Retrieve performance records for a strategy.

**Endpoint**: `GET /workspace/{workspace_id}/strategies/{strategy_id}/performance`

**Parameters**:
- `start_date` (query, optional): Filter by start date
- `end_date` (query, optional): Filter by end date

**Response**:
```json
{
  "performance_records": [
    {
      "id": 1,
      "strategy_id": 123,
      "period_start": "2024-01-01T00:00:00Z",
      "period_end": "2024-01-31T23:59:59Z",
      "total_return": 2500.00,
      "return_percentage": 2.5,
      "sharpe_ratio": 1.8,
      "max_drawdown": 0.05,
      "volatility": 0.08,
      "win_rate": 0.65,
      "total_trades": 20,
      "winning_trades": 13,
      "losing_trades": 7,
      "avg_trade_return": 125.00,
      "performance_data": {
        "monthly_returns": [2.1, 2.8, 1.9, 3.2]
      },
      "created_at": "2024-02-01T00:00:00Z"
    }
  ],
  "total_count": 1
}
```

---

## Strategy Validation

### 12. Validate Strategy

Validate strategy configuration and parameters.

**Endpoint**: `GET /workspace/{workspace_id}/strategies/{strategy_id}/validate`

**Response**:
```json
{
  "strategy_id": 123,
  "is_valid": true,
  "issues": [],
  "warnings": [
    "Strategy has not been backtested recently"
  ],
  "validation_timestamp": "2024-01-01T00:00:00Z"
}
```

---

## Strategy Cloning

### 13. Clone Strategy

Create a copy of an existing strategy.

**Endpoint**: `POST /workspace/{workspace_id}/strategies/{strategy_id}/clone`

**Request Body**:
```json
{
  "new_name": "Cloned Momentum Strategy",
  "target_workspace_id": 2
}
```

**Response**: Returns new strategy object (same as create response)

**Status Code**: `201 Created`

---

## Public Strategies

### 14. Get Public Strategies

Retrieve publicly available strategies that can be cloned.

**Endpoint**: `GET /strategies/public`

**Parameters**:
- `strategy_type` (query, optional): Filter by strategy type
- `page` (query, optional): Page number (default: 1)
- `limit` (query, optional): Items per page (default: 50, max: 100)

**Response**:
```json
{
  "strategies": [
    {
      "id": 456,
      "name": "Public Momentum Strategy",
      "description": "A well-tested momentum strategy",
      "strategy_type": "momentum",
      "risk_level": "medium",
      "created_by": 10,
      "created_at": "2024-01-01T00:00:00Z",
      "parameter_count": 5
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 50
}
```

---

## Error Responses

All endpoints return standard HTTP status codes and error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid strategy type. Must be one of: momentum, mean_reversion, arbitrage, custom"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Strategy not found or access denied"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "strategy_type"],
      "msg": "Strategy type must be one of: momentum, mean_reversion, arbitrage, custom",
      "type": "value_error"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to create strategy: Database connection error"
}
```

---

## Authentication

All API endpoints require authentication using a Bearer token:

```bash
curl -X GET "/workspace/1/strategies" \
  -H "Authorization: Bearer <your_token>"
```

The token should be obtained through the authentication endpoints (not covered in this guide).

---

## Rate Limiting

- **Standard endpoints**: 100 requests per minute per user
- **Analysis/Backtest endpoints**: 10 requests per minute per user
- **Signal generation**: 20 requests per minute per user

---

## Data Types

### Decimal Values
All monetary amounts and percentages are returned as decimal strings for precision:
```json
{
  "total_return": "1234.56",
  "signal_strength": "0.85"
}
```

### Timestamps
All timestamps are in ISO 8601 format with UTC timezone:
```json
{
  "created_at": "2024-01-01T12:30:45Z"
}
```

---

## SDKs and Client Libraries

For easier integration, consider using our official SDKs:

- **Python**: `pip install quant-web-python`
- **JavaScript**: `npm install @quant-web/client`
- **Go**: Available on GitHub

---

## Support

For API support and questions:
- **Documentation**: Check the latest docs at `/docs`
- **Issues**: Report issues on GitHub
- **Community**: Join our Discord community

---

## 🆕 Recent Changes (Strategy Engine Refactoring)

### DataService Integration
- **Real Market Data**: All analysis and signal generation now uses live market data via DataService
- **Improved Analysis**: Strategy analysis includes market data availability and context
- **Better Signal Generation**: Signals generated using actual historical data patterns

### Architecture Changes
- **Backtesting Separated**: Moved to dedicated Backtesting Engine for better modularity
- **Service Layer Pattern**: All engines now use Service Layer for inter-engine communication
- **Improved Error Handling**: Better error messages and data validation

### API Improvements
- **Symbols Parameter**: Analysis and signal generation accept custom symbol lists
- **Deprecation Notices**: Clear migration paths for deprecated endpoints
- **Enhanced Responses**: More detailed analysis results with market context

### Migration Notes
- **Backtest Endpoints**: Use separate Backtesting Engine API
- **Signal Generation**: No longer requires market data in request body
- **Analysis**: Now includes real market data metrics and availability

---

*Last updated: January 2025 - Post Strategy Engine Refactoring*