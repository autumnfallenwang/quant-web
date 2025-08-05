# Portfolio Engine

Core portfolio calculation and analysis engine for quantitative trading operations.

## Components

### PortfolioCalculations
Static methods for financial calculations:
- Position value and P&L calculations  
- Portfolio allocation and risk metrics
- Weighted average price calculations
- Return calculations

### PortfolioEngine  
Main engine class for portfolio operations:
- Comprehensive portfolio analysis
- Trade simulation
- Cash requirement calculations
- Portfolio state validation

## Usage

```python
from backend.core.portfolio_engine import PortfolioEngine

engine = PortfolioEngine()

# Analyze portfolio
analysis = engine.analyze_portfolio(
    portfolio_data={'id': 1, 'initial_cash': Decimal('10000'), 'current_cash': Decimal('5000')},
    positions_data=[{'symbol': 'AAPL', 'quantity': Decimal('10'), 'average_price': Decimal('150')}],
    current_prices={'AAPL': Decimal('160')}
)

# Simulate trade
trade_result = engine.simulate_trade(
    current_position={'quantity': Decimal('10'), 'average_price': Decimal('150')},
    trade_quantity=Decimal('5'),
    trade_price=Decimal('160'),
    trade_type='buy'
)
```

## Key Features

- **Precise Decimal Calculations**: All financial calculations use Decimal for accuracy
- **Comprehensive Analysis**: Portfolio value, P&L, allocation, risk metrics
- **Trade Simulation**: Test trades before execution
- **Validation**: Portfolio state consistency checks
- **Risk Metrics**: Concentration risk and position analysis