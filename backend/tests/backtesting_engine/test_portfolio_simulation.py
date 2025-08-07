# tests/backtesting_engine/test_portfolio_simulation.py
"""
Tests for backtesting portfolio simulation - ensures it behaves like real Portfolio Engine
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from core.backtesting_engine.portfolio import (
    SimulationPortfolio, SimulationPosition, SimulationTransaction
)


class TestSimulationPortfolio:
    """Test that simulation portfolio behaves exactly like real portfolio"""
    
    def test_portfolio_initialization(self):
        """Test portfolio initialization mirrors real Portfolio"""
        initial_cash = Decimal("100000.00")
        portfolio = SimulationPortfolio(initial_cash, "Test Portfolio")
        
        assert portfolio.initial_cash == initial_cash
        assert portfolio.current_cash == initial_cash
        assert portfolio.total_value == initial_cash
        assert portfolio.positions_value == Decimal("0")
        assert len(portfolio.positions) == 0
        assert portfolio.is_active is True
        
    def test_buy_transaction_creates_position(self):
        """Test buy transaction creates position correctly"""
        portfolio = SimulationPortfolio(Decimal("100000"))
        
        # Create buy transaction
        transaction = SimulationTransaction(
            transaction_type="buy",
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            total_amount=Decimal("15000.00"),
            fees=Decimal("1.00")
        )
        
        # Execute transaction
        success = portfolio.execute_transaction(transaction)
        
        assert success is True
        assert portfolio.current_cash == Decimal("84999.00")  # 100000 - 15000 - 1
        assert "AAPL" in portfolio.positions
        
        position = portfolio.positions["AAPL"]
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.average_price == Decimal("150.00")
        assert position.current_price == Decimal("150.00")  # Set to purchase price initially
        
    def test_buy_adds_to_existing_position(self):
        """Test buying more shares updates position with weighted average"""
        portfolio = SimulationPortfolio(Decimal("100000"))
        
        # First purchase
        transaction1 = SimulationTransaction(
            transaction_type="buy",
            symbol="AAPL", 
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            total_amount=Decimal("15000.00"),
            fees=Decimal("0")
        )
        portfolio.execute_transaction(transaction1)
        
        # Second purchase at different price
        transaction2 = SimulationTransaction(
            transaction_type="buy",
            symbol="AAPL",
            quantity=Decimal("50"),
            price=Decimal("160.00"),
            total_amount=Decimal("8000.00"),
            fees=Decimal("0")
        )
        portfolio.execute_transaction(transaction2)
        
        # Check weighted average calculation
        position = portfolio.positions["AAPL"]
        assert position.quantity == Decimal("150")
        
        # Weighted average: (100 * 150 + 50 * 160) / 150 = 153.33
        expected_avg = (Decimal("100") * Decimal("150") + Decimal("50") * Decimal("160")) / Decimal("150")
        assert abs(position.average_price - expected_avg) < Decimal("0.01")
        
    def test_sell_transaction_reduces_position(self):
        """Test sell transaction reduces position correctly"""
        portfolio = SimulationPortfolio(Decimal("100000"))
        
        # Buy shares first
        buy_tx = SimulationTransaction(
            transaction_type="buy",
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            total_amount=Decimal("15000.00"),
            fees=Decimal("0")
        )
        portfolio.execute_transaction(buy_tx)
        
        # Sell some shares
        sell_tx = SimulationTransaction(
            transaction_type="sell", 
            symbol="AAPL",
            quantity=Decimal("30"),
            price=Decimal("160.00"),
            total_amount=Decimal("4800.00"),
            fees=Decimal("0")
        )
        success = portfolio.execute_transaction(sell_tx)
        
        assert success is True
        
        # Check position updated
        position = portfolio.positions["AAPL"]
        assert position.quantity == Decimal("70")  # 100 - 30
        assert position.average_price == Decimal("150.00")  # Unchanged
        
        # Check cash updated
        expected_cash = Decimal("85000") + Decimal("4800")  # Initial remaining + sale proceeds
        assert portfolio.current_cash == expected_cash
        
    def test_sell_all_shares_removes_position(self):
        """Test selling all shares removes position"""
        portfolio = SimulationPortfolio(Decimal("100000"))
        
        # Buy and then sell all
        buy_tx = SimulationTransaction(
            transaction_type="buy",
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            total_amount=Decimal("15000.00"),
            fees=Decimal("0")
        )
        portfolio.execute_transaction(buy_tx)
        
        sell_tx = SimulationTransaction(
            transaction_type="sell",
            symbol="AAPL", 
            quantity=Decimal("100"),
            price=Decimal("160.00"),
            total_amount=Decimal("16000.00"),
            fees=Decimal("0")
        )
        portfolio.execute_transaction(sell_tx)
        
        # Position should be removed
        assert "AAPL" not in portfolio.positions
        assert len(portfolio.positions) == 0
        
    def test_insufficient_cash_blocks_purchase(self):
        """Test that insufficient cash prevents purchase"""
        portfolio = SimulationPortfolio(Decimal("1000"))  # Small amount
        
        # Try to buy more than we can afford
        expensive_tx = SimulationTransaction(
            transaction_type="buy",
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            total_amount=Decimal("15000.00"),
            fees=Decimal("0")
        )
        
        success = portfolio.execute_transaction(expensive_tx)
        
        assert success is False
        assert portfolio.current_cash == Decimal("1000")  # Unchanged
        assert len(portfolio.positions) == 0
        
    def test_insufficient_shares_blocks_sale(self):
        """Test that insufficient shares prevents sale"""
        portfolio = SimulationPortfolio(Decimal("100000"))
        
        # Try to sell shares we don't have
        sell_tx = SimulationTransaction(
            transaction_type="sell",
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            total_amount=Decimal("15000.00"),
            fees=Decimal("0")
        )
        
        success = portfolio.execute_transaction(sell_tx)
        
        assert success is False
        assert portfolio.current_cash == Decimal("100000")  # Unchanged
        
    def test_market_price_updates(self):
        """Test updating market prices updates positions"""
        portfolio = SimulationPortfolio(Decimal("100000"))
        
        # Buy shares
        buy_tx = SimulationTransaction(
            transaction_type="buy",
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            total_amount=Decimal("15000.00"),
            fees=Decimal("0")
        )
        portfolio.execute_transaction(buy_tx)
        
        # Update market prices
        market_data = {"AAPL": Decimal("160.00")}
        portfolio.update_market_prices(market_data)
        
        # Check position updated
        position = portfolio.positions["AAPL"]
        assert position.current_price == Decimal("160.00")
        assert position.market_value == Decimal("16000.00")  # 100 * 160
        assert position.unrealized_pnl == Decimal("1000.00")  # (160-150) * 100
        
    def test_portfolio_value_calculation(self):
        """Test total portfolio value calculation"""
        portfolio = SimulationPortfolio(Decimal("100000"))
        
        # Buy multiple positions
        transactions = [
            SimulationTransaction("buy", "AAPL", Decimal("100"), Decimal("150"), Decimal("15000"), Decimal("0")),
            SimulationTransaction("buy", "MSFT", Decimal("50"), Decimal("250"), Decimal("12500"), Decimal("0"))
        ]
        
        for tx in transactions:
            portfolio.execute_transaction(tx)
        
        # Update market prices
        market_data = {"AAPL": Decimal("160"), "MSFT": Decimal("260")}
        portfolio.update_market_prices(market_data)
        
        # Check calculations
        expected_cash = Decimal("72500")  # 100000 - 15000 - 12500
        expected_positions_value = Decimal("29000")  # 100*160 + 50*260
        expected_total_value = expected_cash + expected_positions_value
        
        assert portfolio.current_cash == expected_cash
        assert portfolio.positions_value == expected_positions_value
        assert portfolio.total_value == expected_total_value
        
    def test_portfolio_summary_matches_real_format(self):
        """Test portfolio summary returns same format as real Portfolio Engine"""
        portfolio = SimulationPortfolio(Decimal("100000"), "Test Portfolio")
        
        # Add some activity
        buy_tx = SimulationTransaction("buy", "AAPL", Decimal("100"), Decimal("150"), Decimal("15000"), Decimal("0"))
        portfolio.execute_transaction(buy_tx)
        
        market_data = {"AAPL": Decimal("160")}
        portfolio.update_market_prices(market_data)
        
        summary = portfolio.get_portfolio_summary()
        
        # Check it has all the same fields as real Portfolio
        required_fields = [
            "name", "description", "initial_cash", "current_cash", "total_value",
            "positions_value", "total_return", "return_percentage", "unrealized_pnl",
            "realized_pnl", "current_drawdown", "peak_value", "position_count",
            "transaction_count", "is_active", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in summary, f"Missing field: {field}"
        
        # Check some calculations
        assert summary["total_return"] == Decimal("1000")  # 101000 - 100000
        assert summary["return_percentage"] == Decimal("1.0")  # 1% return
        assert summary["position_count"] == 1
        assert summary["transaction_count"] == 1
        

class TestSimulationPosition:
    """Test SimulationPosition class"""
    
    def test_position_properties(self):
        """Test position property calculations"""
        position = SimulationPosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            average_price=Decimal("150.00"),
            current_price=Decimal("160.00")
        )
        
        assert position.market_value == Decimal("16000.00")
        assert position.unrealized_pnl == Decimal("1000.00") 
        assert position.cost_basis == Decimal("15000.00")
        
    def test_position_with_no_current_price(self):
        """Test position when current price is None"""
        position = SimulationPosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            average_price=Decimal("150.00"),
            current_price=None
        )
        
        assert position.market_value == Decimal("0")
        assert position.unrealized_pnl == Decimal("0")
        

class TestSimulationTransaction:
    """Test SimulationTransaction class"""
    
    def test_transaction_creation(self):
        """Test transaction creation and properties"""
        tx = SimulationTransaction(
            transaction_type="buy",
            symbol="AAPL", 
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            total_amount=Decimal("15000.00"),
            fees=Decimal("1.00"),
            signal_strength=Decimal("0.8"),
            confidence_score=Decimal("0.9")
        )
        
        assert tx.transaction_type == "buy"
        assert tx.symbol == "AAPL"
        assert tx.quantity == Decimal("100")
        assert tx.price == Decimal("150.00")
        assert tx.total_amount == Decimal("15000.00")
        assert tx.fees == Decimal("1.00")
        assert tx.signal_strength == Decimal("0.8")
        assert tx.confidence_score == Decimal("0.9")
        assert tx.executed_at is not None
        assert tx.created_at is not None


if __name__ == "__main__":
    pytest.main([__file__])