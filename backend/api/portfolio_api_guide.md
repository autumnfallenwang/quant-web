# Portfolio API Guide

> **Complete guide to using the workspace-scoped Portfolio API with practical curl examples**  
> Comprehensive portfolio management, trading, and analysis with consistent URL structure and powerful filtering capabilities.

---

## 🔐 **Authentication**

All API endpoints require authentication using a Bearer token in the Authorization header.

```bash
# Get your token by logging in first
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Response will include access_token
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

**Set your token for all subsequent requests:**
```bash
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

---

## 💰 **Workspace-Scoped Portfolio Operations**

### **List Portfolios in Workspace**
Get all portfolios in a specific workspace with sorting and pagination.

```bash
curl -X GET "http://localhost:8000/workspace/1/portfolios" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "portfolios": [
    {
      "id": 1,
      "name": "Growth Portfolio",
      "description": "High-growth stock portfolio",
      "created_by": 123,
      "workspace_id": 1,
      "initial_cash": 25000.00,
      "current_cash": 18450.75,
      "is_active": true,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T14:30:00Z",
      "position_count": 5,
      "total_value": 28750.25,
      "total_return": 3750.25,
      "return_percentage": 15.00
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 50
}
```

### **Advanced Pagination & Sorting**
Use query parameters to sort and paginate results.

```bash
# Sort by name (ascending)
curl -X GET "http://localhost:8000/workspace/1/portfolios?sort=name&order=asc" \
  -H "Authorization: Bearer $TOKEN"

# Sort by return (descending) with pagination
curl -X GET "http://localhost:8000/workspace/1/portfolios?sort=updated_at&order=desc&page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Combined sorting and pagination
curl -X GET "http://localhost:8000/workspace/1/portfolios?sort=total_return&order=desc&page=1&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Available Sorting:**
- `sort` - Field to sort by: `name`, `created_at`, `updated_at`, `current_cash`, `total_return`
- `order` - Sort order: `asc`, `desc` (default: `desc`)

**Pagination:**
- `page` - Page number (default: 1)
- `limit` - Items per page (1-100, default: 50)

### **Create Portfolio in Workspace**
Create a new portfolio within a specific workspace.

```bash
curl -X POST "http://localhost:8000/workspace/1/portfolios" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Growth Portfolio",
    "description": "Focused on technology stocks with high growth potential",
    "initial_cash": 50000.00
  }'
```

**Response:**
```json
{
  "id": 2,
  "name": "Tech Growth Portfolio",
  "description": "Focused on technology stocks with high growth potential",
  "created_by": 123,
  "workspace_id": 1,
  "initial_cash": 50000.00,
  "current_cash": 50000.00,
  "is_active": true,
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "position_count": 0
}
```

**Required Fields:**
- `name` - Portfolio name (max 100 characters)

**Optional Fields:**
- `description` - Portfolio description (max 500 characters)
- `initial_cash` - Starting cash amount (default: 10000.00, must be >= 0)

---

## 📊 **Single Portfolio Operations**

### **Get Portfolio Details**
Retrieve detailed information about a specific portfolio.

```bash
curl -X GET "http://localhost:8000/workspace/1/portfolios/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "id": 1,
  "name": "Growth Portfolio",
  "description": "High-growth stock portfolio",
  "created_by": 123,
  "workspace_id": 1,
  "initial_cash": 25000.00,
  "current_cash": 18450.75,
  "is_active": true,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T14:30:00Z",
  "position_count": 5
}
```

### **Update Portfolio**
Update portfolio name or description.

```bash
curl -X PATCH "http://localhost:8000/workspace/1/portfolios/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Growth Portfolio",
    "description": "Updated description for high-growth stocks"
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "Updated Growth Portfolio",
  "description": "Updated description for high-growth stocks",
  "created_by": 123,
  "workspace_id": 1,
  "initial_cash": 25000.00,
  "current_cash": 18450.75,
  "is_active": true,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T15:00:00Z",
  "position_count": 5
}
```

---

## 📈 **Portfolio Positions**

### **Get Portfolio Positions**
Retrieve all positions (holdings) for a portfolio with P&L calculations.

```bash
curl -X GET "http://localhost:8000/workspace/1/portfolios/1/positions" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "positions": [
    {
      "id": 1,
      "symbol": "AAPL",
      "quantity": 50.0,
      "average_price": 150.00,
      "current_price": 165.50,
      "position_type": "long",
      "opened_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:30:00Z",
      "market_value": 8275.00,
      "unrealized_pnl": 775.00,
      "unrealized_pnl_percentage": 10.33
    },
    {
      "id": 2,
      "symbol": "GOOGL",
      "quantity": 10.0,
      "average_price": 2800.00,
      "current_price": 2950.00,
      "position_type": "long",
      "opened_at": "2024-01-15T11:00:00Z",
      "updated_at": "2024-01-15T14:30:00Z",
      "market_value": 29500.00,
      "unrealized_pnl": 1500.00,
      "unrealized_pnl_percentage": 5.36
    }
  ],
  "total_count": 2
}
```

**Position Fields:**
- `market_value` - Current market value (quantity × current_price)
- `unrealized_pnl` - Unrealized profit/loss vs cost basis
- `unrealized_pnl_percentage` - P&L as percentage of cost basis

---

## 📋 **Transaction History**

### **Get Portfolio Transactions**
Retrieve transaction history with pagination.

```bash
curl -X GET "http://localhost:8000/workspace/1/portfolios/1/transactions" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "transaction_type": "buy",
      "symbol": "AAPL",
      "quantity": 50.0,
      "price": 150.00,
      "total_amount": 7500.00,
      "fees": 0.00,
      "notes": null,
      "executed_at": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "transaction_type": "buy",
      "symbol": "GOOGL",
      "quantity": 10.0,
      "price": 2800.00,
      "total_amount": 28000.00,
      "fees": 0.00,
      "notes": "Large cap tech purchase",
      "executed_at": "2024-01-15T11:00:00Z",
      "created_at": "2024-01-15T11:00:00Z"
    }
  ],
  "total_count": 2,
  "page": 1,
  "page_size": 50
}
```

### **Paginated Transaction History**
```bash
# Get recent transactions (page 1, 10 items)
curl -X GET "http://localhost:8000/workspace/1/portfolios/1/transactions?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Get older transactions (page 2)
curl -X GET "http://localhost:8000/workspace/1/portfolios/1/transactions?page=2&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 💹 **Trading Operations**

### **Simulate Trade**
Test a trade without executing it to see potential impact.

```bash
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/trades/simulate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "TSLA",
    "quantity": 20.0,
    "price": 245.00,
    "trade_type": "buy"
  }'
```

**Response:**
```json
{
  "can_execute": true,
  "error": null,
  "trade_impact": {
    "symbol": "TSLA",
    "trade_type": "buy",
    "quantity": 20.0,
    "price": 245.00,
    "total_cost": 4900.00
  },
  "portfolio_before": {
    "cash_balance": 18450.75,
    "total_value": 46225.75
  },
  "portfolio_after": {
    "cash_balance": 13550.75,
    "total_value": 46225.75
  },
  "warnings": []
}
```

### **Execute Trade**
Execute a real trade in the portfolio.

```bash
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/trades/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "TSLA",
    "quantity": 20.0,
    "price": 245.00,
    "trade_type": "buy",
    "notes": "Adding Tesla position to portfolio"
  }'
```

**Response:**
```json
{
  "transaction_id": 3,
  "trade_type": "buy",
  "symbol": "TSLA",
  "quantity": 20.0,
  "price": 245.00,
  "total_amount": 4900.00,
  "fees": 0.00,
  "executed_at": "2024-01-15T15:30:00Z",
  "portfolio_cash": 13550.75,
  "position_created": true,
  "position_updated": false,
  "position_closed": false
}
```

### **Sell Position**
```bash
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/trades/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "quantity": 25.0,
    "price": 165.50,
    "trade_type": "sell",
    "notes": "Taking partial profits on AAPL"
  }'
```

**Trade Types:**
- `buy` - Purchase shares (requires sufficient cash)
- `sell` - Sell shares (requires sufficient position)

**Required Fields:**
- `symbol` - Stock symbol (max 10 characters)
- `quantity` - Number of shares (must be > 0)
- `price` - Price per share (must be > 0)
- `trade_type` - Either "buy" or "sell"

**Optional Fields:**
- `notes` - Trade notes (max 500 characters)

---

## 📊 **Portfolio Analysis**

### **Quick Analysis**
Get instant portfolio analysis with key metrics.

```bash
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "quick",
    "include_risk_metrics": true,
    "include_allocation": true
  }'
```

**Response:**
```json
{
  "portfolio_id": 1,
  "analysis_type": "quick",
  "analysis_timestamp": "2024-01-15T15:45:00Z",
  "total_value": 46225.75,
  "cash_balance": 13550.75,
  "positions_value": 32675.00,
  "total_return": 3750.25,
  "return_percentage": 15.00,
  "allocation": {
    "AAPL": 35.89,
    "GOOGL": 63.83,
    "TSLA": 32.11,
    "cash": 29.32
  },
  "risk_metrics": {
    "portfolio_beta": 1.15,
    "max_position_weight": 63.83,
    "concentration_risk": "moderate",
    "diversification_score": 0.75
  },
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 50.0,
      "value": 8275.00,
      "weight": 35.89,
      "pnl": 775.00
    },
    {
      "symbol": "GOOGL",
      "quantity": 10.0,
      "value": 29500.00,
      "weight": 63.83,
      "pnl": 1500.00
    }
  ]
}
```

### **Comprehensive Analysis (Job-Based)**
Start a detailed analysis job for complex portfolio insights.

```bash
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "comprehensive",
    "include_risk_metrics": true,
    "include_allocation": true
  }'
```

**Response:**
```json
{
  "portfolio_id": 1,
  "analysis_type": "comprehensive",
  "analysis_timestamp": "2024-01-15T15:45:00Z",
  "total_value": 0,
  "cash_balance": 0,
  "positions_value": 0,
  "job_id": "job_portfolio_analysis_abc123"
}
```

**Monitor the job:**
```bash
# Check job status
curl -X GET "http://localhost:8000/workspace/1/jobs/job_portfolio_analysis_abc123/status" \
  -H "Authorization: Bearer $TOKEN"

# Get final results when completed
curl -X GET "http://localhost:8000/workspace/1/jobs/job_portfolio_analysis_abc123/result" \
  -H "Authorization: Bearer $TOKEN"
```

**Comprehensive Analysis Result:**
```json
{
  "job_id": "job_portfolio_analysis_abc123",
  "result": {
    "portfolio_analysis": {
      "total_value": 46225.75,
      "total_return": 3750.25,
      "return_percentage": 15.00,
      "sharpe_ratio": 1.25,
      "volatility": 0.18,
      "max_drawdown": 0.05
    },
    "risk_validation": {
      "is_valid": true,
      "issues": [],
      "warnings": ["High concentration in GOOGL (63.83%)"]
    },
    "transaction_analysis": {
      "total_transactions": 10,
      "buy_trades": 7,
      "sell_trades": 3,
      "total_volume": 85000.00,
      "most_traded_symbol": "AAPL",
      "trading_frequency": "moderate"
    },
    "recommendations": [
      "Consider diversifying to reduce concentration risk in GOOGL",
      "Your portfolio shows strong growth momentum",
      "Consider adding fixed income for better risk-adjusted returns"
    ],
    "analysis_timestamp": "2024-01-15T15:50:00Z"
  },
  "status": "success",
  "completed_at": "2024-01-15T15:50:00Z"
}
```

---

## 🔍 **Portfolio Validation**

### **Validate Portfolio State**
Check portfolio for issues, risks, or inconsistencies.

```bash
curl -X GET "http://localhost:8000/workspace/1/portfolios/1/validate" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "portfolio_id": 1,
  "is_valid": true,
  "issues": [],
  "warnings": [
    "High concentration risk: 63.83% in single position (GOOGL)",
    "Cash allocation is above recommended 5% threshold"
  ],
  "validation_timestamp": "2024-01-15T15:45:00Z"
}
```

**Validation with Issues:**
```json
{
  "portfolio_id": 1,
  "is_valid": false,
  "issues": [
    "Negative cash balance: -$1500.00",
    "Position quantity mismatch: AAPL shows 50 shares but transactions total 45"
  ],
  "warnings": [
    "High concentration risk: 90.00% in single position"
  ],
  "validation_timestamp": "2024-01-15T15:45:00Z"
}
```

---

## 🔄 **Legacy Endpoints**

### **List All User Portfolios (Deprecated)**
Get portfolios across all workspaces for backward compatibility.

```bash
curl -X GET "http://localhost:8000/portfolios" \
  -H "Authorization: Bearer $TOKEN"

# With workspace filtering
curl -X GET "http://localhost:8000/portfolios?workspace_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

**⚠️ Note:** This endpoint is deprecated. Use `/workspace/{workspace_id}/portfolios` instead.

---

## 📋 **Quick Reference**

### **URL Patterns**
```bash
# Workspace-Scoped Portfolio Operations
GET    /workspace/{workspace_id}/portfolios                               # List portfolios
POST   /workspace/{workspace_id}/portfolios                               # Create portfolio
GET    /workspace/{workspace_id}/portfolios/{portfolio_id}                # Get portfolio
PATCH  /workspace/{workspace_id}/portfolios/{portfolio_id}                # Update portfolio

# Portfolio Data
GET    /workspace/{workspace_id}/portfolios/{portfolio_id}/positions      # Get positions
GET    /workspace/{workspace_id}/portfolios/{portfolio_id}/transactions   # Get transactions

# Trading Operations
POST   /workspace/{workspace_id}/portfolios/{portfolio_id}/trades/simulate # Simulate trade
POST   /workspace/{workspace_id}/portfolios/{portfolio_id}/trades/execute  # Execute trade

# Analysis & Validation
POST   /workspace/{workspace_id}/portfolios/{portfolio_id}/analyze         # Analyze portfolio
GET    /workspace/{workspace_id}/portfolios/{portfolio_id}/validate        # Validate portfolio

# Legacy (Deprecated)
GET    /portfolios                                                          # List all user portfolios
```

### **Trade Types**
```bash
buy     # Purchase shares (requires sufficient cash)
sell    # Sell shares (requires sufficient position)
```

### **Analysis Types**
```bash
quick           # Instant synchronous analysis
comprehensive   # Detailed job-based analysis with recommendations
```

### **HTTP Status Codes**
```bash
200 OK              # Successful GET, PATCH
201 Created         # Successful POST (portfolio/trade created)
400 Bad Request     # Invalid request data (negative amounts, invalid symbols)
401 Unauthorized    # Missing or invalid token
403 Forbidden       # No access to workspace
404 Not Found       # Portfolio or workspace not found
422 Unprocessable   # Valid JSON but business logic error (insufficient funds)
500 Internal Error  # Server error
```

### **Authentication Headers**
```bash
# Required for all endpoints
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

---

## 🔧 **Complete Examples**

### **Scenario: Create and Trade Portfolio**

```bash
# 1. Create a new portfolio
curl -X POST "http://localhost:8000/workspace/1/portfolios" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dividend Growth Portfolio",
    "description": "Focus on dividend-paying stocks with growth potential",
    "initial_cash": 100000.00
  }'

# Response: {"id": 5, "name": "Dividend Growth Portfolio", ...}

# 2. Simulate a trade first
curl -X POST "http://localhost:8000/workspace/1/portfolios/5/trades/simulate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "MSFT",
    "quantity": 100,
    "price": 380.00,
    "trade_type": "buy"
  }'

# 3. Execute the trade if simulation looks good
curl -X POST "http://localhost:8000/workspace/1/portfolios/5/trades/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "MSFT",
    "quantity": 100,
    "price": 380.00,
    "trade_type": "buy",
    "notes": "Initial MSFT position for dividend growth"
  }'

# 4. Check portfolio positions
curl -X GET "http://localhost:8000/workspace/1/portfolios/5/positions" \
  -H "Authorization: Bearer $TOKEN"
```

### **Scenario: Portfolio Analysis Dashboard**

```bash
# 1. Get all portfolios in workspace
curl -X GET "http://localhost:8000/workspace/1/portfolios?sort=total_return&order=desc" \
  -H "Authorization: Bearer $TOKEN"

# 2. Analyze best performing portfolio
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "quick",
    "include_risk_metrics": true,
    "include_allocation": true
  }'

# 3. Validate portfolio for issues
curl -X GET "http://localhost:8000/workspace/1/portfolios/1/validate" \
  -H "Authorization: Bearer $TOKEN"

# 4. Get recent transaction history
curl -X GET "http://localhost:8000/workspace/1/portfolios/1/transactions?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### **Scenario: Portfolio Rebalancing**

```bash
# 1. Get current positions
curl -X GET "http://localhost:8000/workspace/1/portfolios/1/positions" \
  -H "Authorization: Bearer $TOKEN"

# 2. Simulate selling overweight position
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/trades/simulate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "GOOGL",
    "quantity": 5,
    "price": 2950.00,
    "trade_type": "sell"
  }'

# 3. Execute the rebalancing sell
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/trades/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "GOOGL",
    "quantity": 5,
    "price": 2950.00,
    "trade_type": "sell",
    "notes": "Rebalancing - reducing GOOGL overweight"
  }'

# 4. Use proceeds to buy underweight position
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/trades/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "VTI",
    "quantity": 50,
    "price": 250.00,
    "trade_type": "buy",
    "notes": "Rebalancing - adding broad market exposure"
  }'

# 5. Validate new portfolio allocation
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "quick", "include_allocation": true}'
```

### **Scenario: Comprehensive Analysis Workflow**

```bash
# 1. Start comprehensive analysis (returns job_id)
analysis_job=$(curl -s -X POST "http://localhost:8000/workspace/1/portfolios/1/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "comprehensive"}' | \
  jq -r '.job_id')

echo "Started analysis job: $analysis_job"

# 2. Monitor job progress
while true; do
  status=$(curl -s -X GET "http://localhost:8000/workspace/1/jobs/$analysis_job/status" \
    -H "Authorization: Bearer $TOKEN" | \
    jq -r '.status')
  
  if [ "$status" = "success" ]; then
    echo "Analysis completed!"
    break
  elif [ "$status" = "failed" ]; then
    echo "Analysis failed!"
    exit 1
  else
    echo "Analysis in progress... ($status)"
    sleep 5
  fi
done

# 3. Get comprehensive results
curl -X GET "http://localhost:8000/workspace/1/jobs/$analysis_job/result" \
  -H "Authorization: Bearer $TOKEN" | \
  jq '.result.recommendations'
```

---

## 🚨 **Error Handling Best Practices**

### **Check Response Status**
```bash
# Always check HTTP status code
response=$(curl -w "%{http_code}" -s -o response.json \
  -X GET "http://localhost:8000/workspace/1/portfolios" \
  -H "Authorization: Bearer $TOKEN")

if [ "$response" -eq 200 ]; then
  echo "Success"
  cat response.json
else
  echo "Error: HTTP $response"
  cat response.json
fi
```

### **Handle Trading Errors**
```bash
# Simulate trade first to catch errors
curl -X POST "http://localhost:8000/workspace/1/portfolios/1/trades/simulate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "quantity": 1000,
    "price": 180.00,
    "trade_type": "buy"
  }' | \
jq '.can_execute, .error'

# Output: false, "Insufficient funds: need $180000.00, have $15000.00"
```

### **Handle Common Portfolio Errors**
```bash
# 400 Bad Request - Invalid trade parameters
if [ "$response" -eq 400 ]; then
  echo "Invalid request - check symbol, quantity, and price"
  jq '.detail' response.json
fi

# 422 Unprocessable - Business logic error (insufficient funds/shares)
if [ "$response" -eq 422 ]; then
  echo "Trade cannot be executed:"
  jq '.detail' response.json
fi

# 404 Not Found - Portfolio doesn't exist or no access
if [ "$response" -eq 404 ]; then
  echo "Portfolio not found or access denied"
fi
```

### **Workspace Security**
```bash
# Portfolios are isolated by workspace
# ✅ This works - accessing portfolio in correct workspace
curl -X GET "http://localhost:8000/workspace/1/portfolios/5" \
  -H "Authorization: Bearer $TOKEN"

# ❌ This fails - trying to access portfolio from wrong workspace
curl -X GET "http://localhost:8000/workspace/2/portfolios/5" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 404 "Portfolio not found in specified workspace"
```

---

## 📝 **API Design Patterns**

This Portfolio API follows our consistent design patterns:

1. **URL Structure:** 
   - Workspace-scoped: `/workspace/{workspace_id}/portfolios`
   - Single resource: `/workspace/{workspace_id}/portfolios/{portfolio_id}`
   - Sub-resources: `/workspace/{workspace_id}/portfolios/{portfolio_id}/positions`
   - Actions: `/workspace/{workspace_id}/portfolios/{portfolio_id}/trades/execute`

2. **HTTP Methods:**
   - `GET` - Retrieve data (no body)
   - `POST` - Create resources or execute actions (JSON body)
   - `PATCH` - Update resources (JSON body)

3. **Query Parameters:**
   - Sorting: `?sort=name&order=desc`
   - Pagination: `?page=1&limit=20`

4. **Response Format:**
   - Collections: `{"portfolios": [...], "total_count": N, "page": 1, "page_size": 50}`
   - Single resources: `{portfolio_data}`
   - Errors: `{"detail": "error_message"}`

5. **Workspace Security:**
   - Portfolios are isolated by workspace
   - URL structure enforces permission boundaries
   - Cross-workspace access is prevented

6. **Job Integration:**
   - Long-running operations (comprehensive analysis) use job system
   - Returns job_id for progress tracking
   - Results retrieved via job endpoints

This consistent design makes the Portfolio API predictable and powerful for building portfolio management applications!

---

**🚀 Ready to build sophisticated portfolio management workflows with our Portfolio API!**