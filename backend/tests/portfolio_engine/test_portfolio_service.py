# tests/portfolio_engine/test_portfolio_service.py
"""
Comprehensive tests for portfolio service functions.
Uses real database with proper cleanup and mock data for consistency.
"""
import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlmodel import select

from core.init import run_all
from core.db import get_async_session_context
from services.portfolio_service import (
    create_portfolio,
    get_portfolio,
    get_user_portfolios,
    get_portfolio_positions,
    get_portfolio_transactions,
    analyze_portfolio_quick,
    simulate_trade,
    execute_trade,
    validate_portfolio_state
)
from models.db_models import (
    Portfolio, Position, Transaction, Workspace, WorkspaceMembership,
    UserProfile, IdentityUser
)

# Database Setup
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup database once for all tests"""
    run_all()

@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data():
    """Clean up test data after each test"""
    yield  # Run the test first
    
    # Clean up test data in reverse dependency order
    async with get_async_session_context() as session:
        # Delete transactions
        transaction_result = await session.exec(select(Transaction))
        for transaction in transaction_result.all():
            await session.delete(transaction)
        
        # Delete positions
        position_result = await session.exec(select(Position))
        for position in position_result.all():
            await session.delete(position)
        
        # Delete portfolios
        portfolio_result = await session.exec(select(Portfolio))
        for portfolio in portfolio_result.all():
            await session.delete(portfolio)
        
        # Delete workspace memberships
        membership_result = await session.exec(select(WorkspaceMembership))
        for membership in membership_result.all():
            await session.delete(membership)
        
        # Delete workspaces
        workspace_result = await session.exec(select(Workspace))
        for workspace in workspace_result.all():
            await session.delete(workspace)
        
        # Delete user profiles
        profile_result = await session.exec(select(UserProfile))
        for profile in profile_result.all():
            await session.delete(profile)
        
        # Delete identity users
        identity_result = await session.exec(select(IdentityUser))
        for identity in identity_result.all():
            await session.delete(identity)
            
        await session.commit()

# Test Helpers
async def create_test_user(base_username: str = "testuser") -> int:
    """Helper to create a test user and return their profile ID"""
    username = f"{base_username}_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    
    async with get_async_session_context() as session:
        # Create IdentityUser
        identity_user = IdentityUser(subject=username, issuer="local-idp")
        session.add(identity_user)
        await session.commit()
        await session.refresh(identity_user)
        
        # Create UserProfile
        profile = UserProfile(
            user_id=identity_user.id,
            username=username,
            email=email,
            is_active=True,
            role="user"
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        
        return profile.id

async def create_test_workspace(user_id: int, name: str = "Test Workspace") -> Workspace:
    """Helper to create a test workspace with user membership"""
    workspace_name = f"{name}_{uuid.uuid4().hex[:8]}"
    
    async with get_async_session_context() as session:
        workspace = Workspace(name=workspace_name)
        session.add(workspace)
        await session.flush()
        await session.refresh(workspace)
        
        # Create membership
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_profile_id=user_id,
            role="admin"
        )
        session.add(membership)
        await session.commit()
        await session.refresh(workspace)
        
        return workspace

async def create_test_portfolio(user_id: int, workspace_id: int, name: str = "Test Portfolio", 
                              initial_cash: Decimal = Decimal('10000.00')) -> Portfolio:
    """Helper to create a test portfolio"""
    portfolio_name = f"{name}_{uuid.uuid4().hex[:8]}"
    
    async with get_async_session_context() as session:
        portfolio = Portfolio(
            created_by=user_id,
            workspace_id=workspace_id,
            name=portfolio_name,
            description="Test portfolio",
            initial_cash=initial_cash,
            current_cash=initial_cash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(portfolio)
        await session.commit()
        await session.refresh(portfolio)
        
        return portfolio

async def create_test_position(portfolio_id: int, symbol: str = "AAPL", 
                             quantity: Decimal = Decimal('10'), 
                             avg_price: Decimal = Decimal('150.00'),
                             current_price: Decimal = Decimal('155.00')) -> Position:
    """Helper to create a test position"""
    async with get_async_session_context() as session:
        position = Position(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            average_price=avg_price,
            current_price=current_price,
            updated_at=datetime.now(timezone.utc)
        )
        session.add(position)
        await session.commit()
        await session.refresh(position)
        
        return position

# Mock portfolio engine responses for consistent testing
@pytest.fixture
def mock_portfolio_engine():
    """Mock portfolio engine for predictable test results"""
    with patch('services.portfolio_service.PortfolioEngine') as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Default mock responses
        mock_engine.analyze_portfolio.return_value = {
            'total_value': Decimal('11550.00'),
            'cash_balance': Decimal('1000.00'),
            'positions_value': Decimal('10550.00'),
            'total_return': Decimal('1550.00'),
            'return_percentage': Decimal('15.50'),
            'allocation': {
                'AAPL': Decimal('91.34'),
                'cash': Decimal('8.66')
            },
            'risk_metrics': {
                'portfolio_beta': Decimal('1.15'),
                'max_position_weight': Decimal('91.34')
            },
            'positions': [
                {
                    'symbol': 'AAPL',
                    'quantity': Decimal('10'),
                    'value': Decimal('1550.00'),
                    'weight': Decimal('91.34'),
                    'pnl': Decimal('50.00')
                }
            ],
            'analysis_timestamp': datetime.now(timezone.utc)
        }
        
        mock_engine.simulate_trade.return_value = {
            'can_execute': True,
            'trade_impact': {
                'symbol': 'AAPL',
                'trade_type': 'buy',
                'quantity': Decimal('5'),
                'price': Decimal('150.00'),
                'total_cost': Decimal('750.00')
            },
            'portfolio_after': {
                'cash_balance': Decimal('250.00'),
                'total_value': Decimal('12300.00')
            }
        }
        
        mock_engine.validate_portfolio_state.return_value = {
            'is_valid': True,
            'issues': [],
            'warnings': []
        }
        
        yield mock_engine

# ===== CREATE PORTFOLIO TESTS =====

@pytest.mark.asyncio
async def test_create_portfolio_success():
    """Test successful portfolio creation"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    
    portfolio = await create_portfolio(
        user_id=user_id,
        workspace_id=workspace.id,
        name="My Portfolio",
        description="Test portfolio",
        initial_cash=Decimal('15000.00')
    )
    
    # Assertions
    assert portfolio.name == "My Portfolio"
    assert portfolio.created_by == user_id
    assert portfolio.workspace_id == workspace.id
    assert portfolio.current_cash == Decimal('15000.00')
    assert portfolio.initial_cash == Decimal('15000.00')
    assert portfolio.id is not None

@pytest.mark.asyncio
async def test_create_portfolio_no_workspace_access():
    """Test portfolio creation fails without workspace access"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    workspace = await create_test_workspace(user1_id, "Private Workspace")
    
    # user2 should not be able to create portfolio in user1's workspace
    with pytest.raises(ValueError, match="does not have access to workspace"):
        await create_portfolio(
            user_id=user2_id,
            workspace_id=workspace.id,
            name="Unauthorized Portfolio"
        )

@pytest.mark.asyncio
async def test_create_portfolio_duplicate_name():
    """Test portfolio creation fails with duplicate name in same workspace"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    
    # Create first portfolio
    await create_portfolio(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Duplicate Name"
    )
    
    # Try to create second with same name
    with pytest.raises(ValueError, match="already exists in this workspace"):
        await create_portfolio(
            user_id=user_id,
            workspace_id=workspace.id,
            name="Duplicate Name"
        )

# ===== GET PORTFOLIO TESTS =====

@pytest.mark.asyncio
async def test_get_portfolio_success():
    """Test successful portfolio retrieval"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio")
    
    retrieved = await get_portfolio(portfolio.id, user_id)
    
    # Assertions
    assert retrieved.id == portfolio.id
    assert retrieved.name == portfolio.name
    assert retrieved.created_by == user_id

@pytest.mark.asyncio
async def test_get_portfolio_no_access():
    """Test portfolio retrieval fails without access"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    workspace = await create_test_workspace(user1_id, "Private Workspace")
    portfolio = await create_test_portfolio(user1_id, workspace.id, "Private Portfolio")
    
    # user2 should not be able to get user1's portfolio
    with pytest.raises(ValueError, match="not found or access denied"):
        await get_portfolio(portfolio.id, user2_id)

@pytest.mark.asyncio
async def test_get_portfolio_not_found():
    """Test portfolio retrieval with non-existent portfolio"""
    user_id = await create_test_user("user1")
    
    with pytest.raises(ValueError, match="not found or access denied"):
        await get_portfolio(999, user_id)

# ===== GET USER PORTFOLIOS TESTS =====

@pytest.mark.asyncio
async def test_get_user_portfolios_success():
    """Test getting user portfolios successfully"""
    user_id = await create_test_user("user1")
    workspace1 = await create_test_workspace(user_id, "Workspace 1")
    workspace2 = await create_test_workspace(user_id, "Workspace 2")
    
    # Create portfolios in different workspaces
    portfolio1 = await create_test_portfolio(user_id, workspace1.id, "Portfolio 1")
    portfolio2 = await create_test_portfolio(user_id, workspace2.id, "Portfolio 2")
    portfolio3 = await create_test_portfolio(user_id, workspace1.id, "Portfolio 3")
    
    # Get all portfolios
    portfolios = await get_user_portfolios(user_id)
    
    # Assertions
    assert len(portfolios) == 3
    portfolio_ids = [p.id for p in portfolios]
    assert portfolio1.id in portfolio_ids
    assert portfolio2.id in portfolio_ids
    assert portfolio3.id in portfolio_ids

@pytest.mark.asyncio
async def test_get_user_portfolios_filtered_by_workspace():
    """Test getting user portfolios filtered by workspace"""
    user_id = await create_test_user("user1")
    workspace1 = await create_test_workspace(user_id, "Workspace 1")
    workspace2 = await create_test_workspace(user_id, "Workspace 2")
    
    portfolio1 = await create_test_portfolio(user_id, workspace1.id, "Portfolio 1")
    portfolio2 = await create_test_portfolio(user_id, workspace2.id, "Portfolio 2")
    
    # Get portfolios for workspace1 only
    portfolios = await get_user_portfolios(user_id, workspace1.id)
    
    # Assertions
    assert len(portfolios) == 1
    assert portfolios[0].id == portfolio1.id

@pytest.mark.asyncio
async def test_get_user_portfolios_empty():
    """Test getting portfolios when user has none"""
    user_id = await create_test_user("user1")
    
    portfolios = await get_user_portfolios(user_id)
    
    assert portfolios == []

# ===== PORTFOLIO POSITIONS TESTS =====

@pytest.mark.asyncio
async def test_get_portfolio_positions_success():
    """Test getting portfolio positions successfully"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio")
    
    # Create test positions
    position1 = await create_test_position(portfolio.id, "AAPL", Decimal('10'), Decimal('150.00'))
    position2 = await create_test_position(portfolio.id, "GOOGL", Decimal('5'), Decimal('2500.00'))
    
    positions = await get_portfolio_positions(portfolio.id, user_id)
    
    # Assertions
    assert len(positions) == 2
    symbols = [p.symbol for p in positions]
    assert "AAPL" in symbols
    assert "GOOGL" in symbols

@pytest.mark.asyncio
async def test_get_portfolio_positions_no_access():
    """Test getting positions fails without portfolio access"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    workspace = await create_test_workspace(user1_id, "Private Workspace")
    portfolio = await create_test_portfolio(user1_id, workspace.id, "Private Portfolio")
    
    with pytest.raises(ValueError, match="not found or access denied"):
        await get_portfolio_positions(portfolio.id, user2_id)

# ===== PORTFOLIO ANALYSIS TESTS =====

@pytest.mark.asyncio
async def test_analyze_portfolio_quick_success(mock_portfolio_engine):
    """Test quick portfolio analysis"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio")
    await create_test_position(portfolio.id, "AAPL", Decimal('10'), Decimal('150.00'))
    
    analysis = await analyze_portfolio_quick(portfolio.id, user_id)
    
    # Assertions
    assert 'total_value' in analysis
    assert 'positions' in analysis
    assert 'risk_metrics' in analysis
    assert mock_portfolio_engine.analyze_portfolio.called

@pytest.mark.asyncio
async def test_analyze_portfolio_no_positions(mock_portfolio_engine):
    """Test portfolio analysis with no positions"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Empty Portfolio")
    
    analysis = await analyze_portfolio_quick(portfolio.id, user_id)
    
    # Should still work with empty positions
    assert mock_portfolio_engine.analyze_portfolio.called

# ===== TRADE SIMULATION TESTS =====

@pytest.mark.asyncio
async def test_simulate_trade_success(mock_portfolio_engine):
    """Test successful trade simulation"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio")
    await create_test_position(portfolio.id, "AAPL", Decimal('10'), Decimal('150.00'))
    
    simulation = await simulate_trade(
        portfolio_id=portfolio.id,
        user_id=user_id,
        symbol="AAPL",
        quantity=Decimal('5'),
        price=Decimal('150.00'),
        trade_type="buy"
    )
    
    # Assertions
    assert 'can_execute' in simulation
    assert 'trade_impact' in simulation
    assert mock_portfolio_engine.simulate_trade.called

@pytest.mark.asyncio
async def test_simulate_trade_no_access(mock_portfolio_engine):
    """Test trade simulation fails without portfolio access"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    workspace = await create_test_workspace(user1_id, "Private Workspace")
    portfolio = await create_test_portfolio(user1_id, workspace.id, "Private Portfolio")
    
    with pytest.raises(ValueError, match="not found or access denied"):
        await simulate_trade(
            portfolio_id=portfolio.id,
            user_id=user2_id,
            symbol="AAPL",
            quantity=Decimal('5'),
            price=Decimal('150.00'),
            trade_type="buy"
        )

# ===== TRADE EXECUTION TESTS =====

@pytest.mark.asyncio
async def test_execute_trade_buy_success(mock_portfolio_engine):
    """Test successful buy trade execution"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio", Decimal('10000.00'))
    
    transaction = await execute_trade(
        portfolio_id=portfolio.id,
        user_id=user_id,
        symbol="AAPL",
        quantity=Decimal('10'),
        price=Decimal('150.00'),
        trade_type="buy"
    )
    
    # Assertions
    assert transaction.symbol == "AAPL"
    assert transaction.quantity == Decimal('10')
    assert transaction.price == Decimal('150.00')
    assert transaction.transaction_type == "buy"
    assert transaction.total_amount == Decimal('1500.00')
    
    # Verify position was created
    positions = await get_portfolio_positions(portfolio.id, user_id)
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].quantity == Decimal('10')

@pytest.mark.asyncio
async def test_execute_trade_sell_success(mock_portfolio_engine):
    """Test successful sell trade execution"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio", Decimal('5000.00'))
    
    # Create existing position
    await create_test_position(portfolio.id, "AAPL", Decimal('10'), Decimal('150.00'))
    
    transaction = await execute_trade(
        portfolio_id=portfolio.id,
        user_id=user_id,
        symbol="AAPL",
        quantity=Decimal('5'),
        price=Decimal('155.00'),
        trade_type="sell"
    )
    
    # Assertions
    assert transaction.transaction_type == "sell"
    assert transaction.total_amount == Decimal('775.00')
    
    # Verify position was updated
    positions = await get_portfolio_positions(portfolio.id, user_id)
    assert len(positions) == 1
    assert positions[0].quantity == Decimal('5')  # 10 - 5 = 5

@pytest.mark.asyncio
async def test_execute_trade_cannot_execute(mock_portfolio_engine):
    """Test trade execution fails when simulation says it cannot execute"""
    # Mock simulation to return cannot execute
    mock_portfolio_engine.simulate_trade.return_value = {
        'can_execute': False,
        'error': 'Insufficient funds'
    }
    
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio", Decimal('100.00'))
    
    with pytest.raises(ValueError, match="Insufficient funds"):
        await execute_trade(
            portfolio_id=portfolio.id,
            user_id=user_id,
            symbol="AAPL",
            quantity=Decimal('100'),
            price=Decimal('150.00'),
            trade_type="buy"
        )

# ===== PORTFOLIO VALIDATION TESTS =====

@pytest.mark.asyncio
async def test_validate_portfolio_state_success(mock_portfolio_engine):
    """Test portfolio state validation"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio")
    await create_test_position(portfolio.id, "AAPL", Decimal('10'), Decimal('150.00'))
    
    validation = await validate_portfolio_state(portfolio.id, user_id)
    
    # Assertions
    assert 'is_valid' in validation
    assert 'issues' in validation
    assert 'warnings' in validation
    assert mock_portfolio_engine.validate_portfolio_state.called

@pytest.mark.asyncio
async def test_get_portfolio_transactions_success():
    """Test getting portfolio transaction history"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio")
    
    # Create test transactions directly in DB
    async with get_async_session_context() as session:
        transaction1 = Transaction(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            quantity=Decimal('10'),
            price=Decimal('150.00'),
            transaction_type="buy",
            total_amount=Decimal('1500.00'),
            created_by=user_id,
            executed_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        transaction2 = Transaction(
            portfolio_id=portfolio.id,
            symbol="GOOGL",
            quantity=Decimal('5'),
            price=Decimal('2500.00'),
            transaction_type="buy",
            total_amount=Decimal('12500.00'),
            created_by=user_id,
            executed_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        session.add(transaction1)
        session.add(transaction2)
        await session.commit()
    
    transactions = await get_portfolio_transactions(portfolio.id, user_id)
    
    # Assertions
    assert len(transactions) == 2
    symbols = [t.symbol for t in transactions]
    assert "AAPL" in symbols
    assert "GOOGL" in symbols

@pytest.mark.asyncio
async def test_get_portfolio_transactions_pagination():
    """Test transaction history pagination"""
    user_id = await create_test_user("user1")
    workspace = await create_test_workspace(user_id, "Test Workspace")
    portfolio = await create_test_portfolio(user_id, workspace.id, "Test Portfolio")
    
    # Create multiple transactions
    async with get_async_session_context() as session:
        for i in range(5):
            transaction = Transaction(
                portfolio_id=portfolio.id,
                symbol=f"STOCK{i}",
                quantity=Decimal('1'),
                price=Decimal('100.00'),
                transaction_type="buy",
                total_amount=Decimal('100.00'),
                created_by=user_id,
                executed_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            session.add(transaction)
        await session.commit()
    
    # Test pagination
    transactions_page1 = await get_portfolio_transactions(portfolio.id, user_id, limit=3, offset=0)
    transactions_page2 = await get_portfolio_transactions(portfolio.id, user_id, limit=3, offset=3)
    
    # Assertions
    assert len(transactions_page1) == 3
    assert len(transactions_page2) == 2
    
    # Should be different transactions
    page1_ids = [t.id for t in transactions_page1]
    page2_ids = [t.id for t in transactions_page2]
    assert not set(page1_ids).intersection(set(page2_ids))