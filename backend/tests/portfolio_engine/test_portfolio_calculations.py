# tests/portfolio_engine/test_portfolio_calculations.py
import pytest
from decimal import Decimal
from pathlib import Path
import sys

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.portfolio_engine.calculations import PortfolioCalculations


class TestPortfolioCalculations:
    """Test suite for portfolio calculation functions"""
    
    def test_calculate_position_value(self):
        """Test position value calculation"""
        quantity = Decimal('10')
        price = Decimal('150.50')
        expected = Decimal('1505.00')
        
        result = PortfolioCalculations.calculate_position_value(quantity, price)
        assert result == expected
    
    def test_calculate_position_pnl_profit(self):
        """Test P&L calculation with profit"""
        quantity = Decimal('10')
        avg_price = Decimal('100.00')
        current_price = Decimal('120.00')
        
        pnl, pnl_percent = PortfolioCalculations.calculate_position_pnl(
            quantity, avg_price, current_price
        )
        
        assert pnl == Decimal('200.00')  # (120-100) * 10
        assert pnl_percent == Decimal('20.00')  # 20% gain
    
    def test_calculate_position_pnl_loss(self):
        """Test P&L calculation with loss"""
        quantity = Decimal('10')
        avg_price = Decimal('100.00')
        current_price = Decimal('85.00')
        
        pnl, pnl_percent = PortfolioCalculations.calculate_position_pnl(
            quantity, avg_price, current_price
        )
        
        assert pnl == Decimal('-150.00')  # (85-100) * 10
        assert pnl_percent == Decimal('-15.00')  # 15% loss
    
    def test_calculate_portfolio_value(self):
        """Test total portfolio value calculation"""
        cash = Decimal('5000.00')
        positions = [
            {'quantity': Decimal('10'), 'current_price': Decimal('150.00')},
            {'quantity': Decimal('20'), 'current_price': Decimal('50.00')}
        ]
        
        result = PortfolioCalculations.calculate_portfolio_value(cash, positions)
        expected = Decimal('7500.00')  # 5000 + (10*150) + (20*50)
        
        assert result == expected
    
    def test_calculate_portfolio_allocation(self):
        """Test portfolio allocation percentage calculation"""
        cash = Decimal('2000.00')
        positions = [
            {'symbol': 'AAPL', 'quantity': Decimal('10'), 'current_price': Decimal('100.00')},
            {'symbol': 'MSFT', 'quantity': Decimal('10'), 'current_price': Decimal('300.00')}
        ]
        
        allocation = PortfolioCalculations.calculate_portfolio_allocation(cash, positions)
        
        # Total value: 2000 + 1000 + 3000 = 6000
        assert allocation['CASH'] == Decimal('33.33')  # 2000/6000 * 100
        assert allocation['AAPL'] == Decimal('16.67')  # 1000/6000 * 100
        assert allocation['MSFT'] == Decimal('50.00')  # 3000/6000 * 100
    
    def test_calculate_weighted_average_price_new_position(self):
        """Test weighted average price for new position"""
        result = PortfolioCalculations.calculate_weighted_average_price(
            Decimal('0'), Decimal('0'), Decimal('10'), Decimal('100.00')
        )
        assert result == Decimal('100.0000')
    
    def test_calculate_weighted_average_price_add_to_position(self):
        """Test weighted average price when adding to existing position"""
        # Current: 10 shares at $100, Adding: 10 shares at $120
        # New average: (10*100 + 10*120) / 20 = 110
        result = PortfolioCalculations.calculate_weighted_average_price(
            Decimal('10'), Decimal('100.00'), Decimal('10'), Decimal('120.00')
        )
        assert result == Decimal('110.0000')
    
    def test_calculate_portfolio_returns_profit(self):
        """Test portfolio return calculation with profit"""
        current_value = Decimal('12000.00')
        initial_value = Decimal('10000.00')
        
        abs_return, pct_return = PortfolioCalculations.calculate_portfolio_returns(
            current_value, initial_value
        )
        
        assert abs_return == Decimal('2000.00')
        assert pct_return == Decimal('20.00')
    
    def test_calculate_portfolio_returns_with_cash_flows(self):
        """Test portfolio return calculation with cash flows"""
        current_value = Decimal('12000.00')
        initial_value = Decimal('10000.00')
        cash_flows = Decimal('1000.00')  # $1000 deposit
        
        abs_return, pct_return = PortfolioCalculations.calculate_portfolio_returns(
            current_value, initial_value, cash_flows
        )
        
        # Adjusted initial: 10000 + 1000 = 11000
        # Return: 12000 - 11000 = 1000 (9.09%)
        assert abs_return == Decimal('1000.00')
        assert pct_return == Decimal('9.09')
    
    def test_calculate_risk_metrics(self):
        """Test risk metrics calculation"""
        positions = [
            {'symbol': 'AAPL', 'quantity': Decimal('10'), 'current_price': Decimal('100.00')},
            {'symbol': 'MSFT', 'quantity': Decimal('10'), 'current_price': Decimal('300.00')},
            {'symbol': 'GOOGL', 'quantity': Decimal('5'), 'current_price': Decimal('200.00')}
        ]
        
        metrics = PortfolioCalculations.calculate_risk_metrics(positions)
        
        # Total value: 1000 + 3000 + 1000 = 5000
        # MSFT is largest at 3000/5000 = 60%
        assert metrics['concentration_risk'] == Decimal('60.00')
        assert metrics['largest_position'] == Decimal('60.00')
        assert metrics['position_count'] == 3
    
    def test_calculate_risk_metrics_empty_positions(self):
        """Test risk metrics with no positions"""
        positions = []
        metrics = PortfolioCalculations.calculate_risk_metrics(positions)
        
        assert metrics['concentration_risk'] == Decimal('0.00')
        assert metrics['largest_position'] == Decimal('0.00')
        assert metrics['position_count'] == 0