# tests/portfolio_engine/test_portfolio_engine.py
import pytest
from decimal import Decimal
from pathlib import Path
import sys

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.portfolio_engine.engine import PortfolioEngine


class TestPortfolioEngine:
    """Test suite for portfolio engine operations"""
    
    @pytest.fixture
    def engine(self):
        """Create portfolio engine instance"""
        return PortfolioEngine()
    
    @pytest.fixture
    def sample_portfolio_data(self):
        """Sample portfolio data for testing"""
        return {
            'id': 1,
            'initial_cash': Decimal('10000.00'),
            'current_cash': Decimal('5000.00')
        }
    
    @pytest.fixture
    def sample_positions_data(self):
        """Sample positions data for testing"""
        return [
            {
                'symbol': 'AAPL',
                'quantity': Decimal('10'),
                'average_price': Decimal('150.00')
            },
            {
                'symbol': 'MSFT',
                'quantity': Decimal('5'),
                'average_price': Decimal('300.00')
            }
        ]
    
    @pytest.fixture
    def sample_current_prices(self):
        """Sample current prices for testing"""
        return {
            'AAPL': Decimal('160.00'),
            'MSFT': Decimal('320.00')
        }
    
    def test_analyze_portfolio(self, engine, sample_portfolio_data, sample_positions_data, sample_current_prices):
        """Test comprehensive portfolio analysis"""
        analysis = engine.analyze_portfolio(
            sample_portfolio_data,
            sample_positions_data,
            sample_current_prices
        )
        
        # Check structure
        assert 'portfolio_id' in analysis
        assert 'summary' in analysis
        assert 'allocation' in analysis
        assert 'risk_metrics' in analysis
        assert 'positions' in analysis
        assert 'analysis_timestamp' in analysis
        
        # Check summary values
        summary = analysis['summary']
        expected_total = Decimal('8200.00')  # 5000 + (10*160) + (5*320)
        assert summary['total_value'] == expected_total
        assert summary['cash'] == Decimal('5000.00')
        assert summary['positions_value'] == Decimal('3200.00')
        assert summary['position_count'] == 2
        
        # Check positions details
        positions = analysis['positions']
        assert len(positions) == 2
        
        aapl_position = next(p for p in positions if p['symbol'] == 'AAPL')
        assert aapl_position['market_value'] == Decimal('1600.00')
        assert aapl_position['unrealized_pnl'] == Decimal('100.00')  # (160-150)*10
        assert aapl_position['unrealized_pnl_percent'] == Decimal('6.67')
    
    def test_simulate_trade_buy(self, engine):
        """Test buy trade simulation"""
        current_position = {
            'quantity': Decimal('10'),
            'average_price': Decimal('100.00')
        }
        
        result = engine.simulate_trade(
            current_position,
            Decimal('5'),
            Decimal('120.00'),
            'buy'
        )
        
        # New quantity: 10 + 5 = 15
        # New average: (10*100 + 5*120) / 15 = 106.67
        assert result['new_quantity'] == Decimal('15')
        assert result['new_average_price'] == Decimal('106.6667')
        assert result['trade_value'] == Decimal('600.00')
        assert result['trade_type'] == 'buy'
    
    def test_simulate_trade_sell(self, engine):
        """Test sell trade simulation"""
        current_position = {
            'quantity': Decimal('10'),
            'average_price': Decimal('100.00')
        }
        
        result = engine.simulate_trade(
            current_position,
            Decimal('3'),
            Decimal('120.00'),
            'sell'
        )
        
        # New quantity: 10 - 3 = 7
        # Average price stays the same on sell
        assert result['new_quantity'] == Decimal('7')
        assert result['new_average_price'] == Decimal('100.00')
        assert result['trade_value'] == Decimal('360.00')
        assert result['trade_type'] == 'sell'
    
    def test_simulate_trade_sell_too_much(self, engine):
        """Test selling more than available quantity"""
        current_position = {
            'quantity': Decimal('10'),
            'average_price': Decimal('100.00')
        }
        
        with pytest.raises(ValueError, match="Cannot sell 15 shares, only 10 available"):
            engine.simulate_trade(
                current_position,
                Decimal('15'),
                Decimal('120.00'),
                'sell'
            )
    
    def test_simulate_trade_new_position(self, engine):
        """Test trade simulation with no existing position"""
        result = engine.simulate_trade(
            None,
            Decimal('10'),
            Decimal('100.00'),
            'buy'
        )
        
        assert result['new_quantity'] == Decimal('10')
        assert result['new_average_price'] == Decimal('100.00')
        assert result['trade_value'] == Decimal('1000.00')
    
    def test_calculate_required_cash(self, engine):
        """Test cash requirement calculation"""
        trades = [
            {
                'trade_type': 'buy',
                'quantity': Decimal('10'),
                'price': Decimal('100.00'),
                'fees': Decimal('5.00')
            },
            {
                'trade_type': 'buy',
                'quantity': Decimal('5'),
                'price': Decimal('200.00'),
                'fees': Decimal('2.50')
            },
            {
                'trade_type': 'sell',
                'quantity': Decimal('2'),
                'price': Decimal('150.00')
            }
        ]
        
        required_cash = engine.calculate_required_cash(trades)
        # Buy trades only: (10*100 + 5) + (5*200 + 2.50) = 1005 + 1002.50 = 2007.50
        assert required_cash == Decimal('2007.50')
    
    def test_validate_portfolio_state_valid(self, engine):
        """Test portfolio state validation with valid portfolio"""
        cash = Decimal('1000.00')
        positions = [
            {
                'symbol': 'AAPL',
                'quantity': Decimal('10'),
                'average_price': Decimal('100.00'),
                'current_price': Decimal('110.00')
            }
        ]
        
        validation = engine.validate_portfolio_state(cash, positions)
        
        assert validation['is_valid'] is True
        assert len(validation['issues']) == 0
        assert len(validation['warnings']) == 1
        assert 'High concentration risk' in validation['warnings'][0]
    
    def test_validate_portfolio_state_negative_cash(self, engine):
        """Test portfolio state validation with negative cash"""
        cash = Decimal('-100.00')
        positions = []
        
        validation = engine.validate_portfolio_state(cash, positions)
        
        assert validation['is_valid'] is False
        assert 'negative cash' in validation['issues'][0].lower()
    
    def test_validate_portfolio_state_high_concentration(self, engine):
        """Test portfolio state validation with high concentration risk"""
        cash = Decimal('100.00')
        positions = [
            {
                'symbol': 'AAPL',
                'quantity': Decimal('100'),
                'average_price': Decimal('100.00'),
                'current_price': Decimal('100.00')
            }
        ]
        
        validation = engine.validate_portfolio_state(cash, positions)
        
        assert validation['is_valid'] is True  # Valid but has warnings
        assert len(validation['warnings']) > 0
        assert 'concentration risk' in validation['warnings'][0].lower()