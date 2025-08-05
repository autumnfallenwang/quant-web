# tests/portfolio_engine/test_portfolio_api.py
"""
Comprehensive tests for portfolio API endpoints.
Uses real database with proper cleanup and follows established patterns.
"""
import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlmodel import select

from core.init import run_all
from core.db import get_async_session_context
from models.db_models import (
    Portfolio, Position, Transaction, Workspace, WorkspaceMembership,
    UserProfile, IdentityUser
)

# Import the FastAPI app (you'll need to adjust this import based on your app structure)
# from main import app  # Adjust this import

# For now, we'll test the service integration without full FastAPI integration
# This follows the same pattern as existing tests

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

async def create_test_user_profile(user_id: int) -> UserProfile:
    """Helper to get UserProfile for testing dependencies"""
    async with get_async_session_context() as session:
        result = await session.exec(select(UserProfile).where(UserProfile.id == user_id))
        return result.first()

# Mock API dependencies
@pytest.fixture
def mock_get_current_user():
    """Mock the get_current_user dependency"""
    async def _mock_get_current_user():
        # This would return a UserProfile instance
        # For now, we'll mock it
        return MagicMock(id=1, username="testuser", email="test@example.com")
    
    return _mock_get_current_user

@pytest.fixture
def mock_portfolio_engine():
    """Mock portfolio engine for predictable test results"""
    with patch('api.portfolio.analyze_portfolio_quick') as mock_quick, \
         patch('api.portfolio.analyze_portfolio_comprehensive') as mock_comprehensive, \
         patch('api.portfolio.simulate_trade') as mock_simulate, \
         patch('api.portfolio.execute_trade') as mock_execute:
        
        # Configure mock responses
        mock_quick.return_value = {
            'total_value': Decimal('11550.00'),
            'cash_balance': Decimal('1000.00'),
            'positions_value': Decimal('10550.00'),
            'total_return': Decimal('1550.00'),
            'return_percentage': Decimal('15.50'),
            'allocation': {'AAPL': Decimal('91.34'), 'cash': Decimal('8.66')},
            'risk_metrics': {'portfolio_beta': Decimal('1.15')},
            'positions': [{'symbol': 'AAPL', 'quantity': Decimal('10')}],
            'analysis_timestamp': datetime.now(timezone.utc)
        }
        
        mock_comprehensive.return_value = "job_123"
        
        mock_simulate.return_value = {
            'can_execute': True,
            'trade_impact': {'symbol': 'AAPL', 'cost': Decimal('750.00')},
            'portfolio_after': {'cash_balance': Decimal('250.00')}
        }
        
        # Mock transaction for execute_trade
        mock_transaction = MagicMock()
        mock_transaction.id = 1
        mock_transaction.symbol = "AAPL"
        mock_transaction.quantity = Decimal('5')
        mock_transaction.price = Decimal('150.00')
        mock_transaction.transaction_type = "buy"
        mock_transaction.total_amount = Decimal('750.00')
        mock_transaction.fees = Decimal('0.00')
        mock_transaction.executed_at = datetime.now(timezone.utc)
        mock_execute.return_value = mock_transaction
        
        yield {
            'quick': mock_quick,
            'comprehensive': mock_comprehensive,
            'simulate': mock_simulate,
            'execute': mock_execute
        }

# ===== PORTFOLIO API INTEGRATION TESTS =====
# These test the integration between API layer and service layer

@pytest.mark.asyncio
async def test_portfolio_api_integration_flow():
    """Test the complete portfolio API integration flow"""
    # Create test data
    user_id = await create_test_user("portfolio_api_user")
    workspace = await create_test_workspace(user_id, "API Test Workspace")
    
    # Import service functions to test integration
    from services.portfolio_service import (
        create_portfolio, get_portfolio, get_user_portfolios,
        analyze_portfolio_quick, simulate_trade
    )
    
    # Test 1: Create Portfolio (simulating API create request)
    portfolio = await create_portfolio(
        user_id=user_id,
        workspace_id=workspace.id,
        name="API Test Portfolio",
        description="Portfolio created via API test",
        initial_cash=Decimal('15000.00')
    )
    
    assert portfolio.name == "API Test Portfolio"
    assert portfolio.workspace_id == workspace.id
    assert portfolio.current_cash == Decimal('15000.00')
    
    # Test 2: Get Portfolio (simulating API get request)
    retrieved_portfolio = await get_portfolio(portfolio.id, user_id)
    assert retrieved_portfolio.id == portfolio.id
    assert retrieved_portfolio.name == "API Test Portfolio"
    
    # Test 3: List User Portfolios (simulating API list request)
    portfolios = await get_user_portfolios(user_id, workspace.id)
    assert len(portfolios) == 1
    assert portfolios[0].id == portfolio.id
    
    # Test 4: Portfolio Analysis (simulating API analysis request)
    with patch('services.portfolio_service.PortfolioEngine') as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.analyze_portfolio.return_value = {
            'total_value': Decimal('15000.00'),
            'cash_balance': Decimal('15000.00'),
            'positions_value': Decimal('0.00'),
            'allocation': {'cash': Decimal('100.00')},
            'risk_metrics': {},
            'positions': [],
            'analysis_timestamp': datetime.now(timezone.utc)
        }
        
        analysis = await analyze_portfolio_quick(portfolio.id, user_id)
        assert analysis['total_value'] == Decimal('15000.00')
        assert analysis['cash_balance'] == Decimal('15000.00')
    
    # Test 5: Trade Simulation (simulating API trade simulation request)
    with patch('services.portfolio_service.PortfolioEngine') as mock_engine_class:
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.simulate_trade.return_value = {
            'can_execute': True,
            'trade_impact': {
                'symbol': 'AAPL',
                'trade_type': 'buy',
                'quantity': Decimal('10'),
                'total_cost': Decimal('1500.00')
            },
            'portfolio_after': {
                'cash_balance': Decimal('13500.00')
            }
        }
        
        simulation = await simulate_trade(
            portfolio_id=portfolio.id,
            user_id=user_id,
            symbol="AAPL",
            quantity=Decimal('10'),
            price=Decimal('150.00'),
            trade_type="buy"
        )
        
        assert simulation['can_execute'] is True
        assert simulation['trade_impact']['symbol'] == 'AAPL'

@pytest.mark.asyncio
async def test_portfolio_api_error_handling():
    """Test API error handling scenarios"""
    user_id = await create_test_user("error_test_user")
    workspace = await create_test_workspace(user_id, "Error Test Workspace")
    
    from services.portfolio_service import get_portfolio, create_portfolio
    
    # Test 1: Portfolio not found
    with pytest.raises(ValueError, match="not found or access denied"):
        await get_portfolio(999, user_id)
    
    # Test 2: Access denied (different user)
    other_user_id = await create_test_user("other_user")
    portfolio = await create_portfolio(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Private Portfolio"
    )
    
    with pytest.raises(ValueError, match="not found or access denied"):
        await get_portfolio(portfolio.id, other_user_id)

@pytest.mark.asyncio
async def test_portfolio_api_workspace_validation():
    """Test workspace validation in API endpoints"""
    user1_id = await create_test_user("workspace_user1")
    user2_id = await create_test_user("workspace_user2")
    
    workspace1 = await create_test_workspace(user1_id, "Workspace 1")
    workspace2 = await create_test_workspace(user2_id, "Workspace 2")
    
    from services.portfolio_service import create_portfolio, get_portfolio
    
    # Create portfolio in workspace1
    portfolio = await create_portfolio(
        user_id=user1_id,
        workspace_id=workspace1.id,
        name="Workspace 1 Portfolio"
    )
    
    # User1 can access portfolio in their workspace
    retrieved = await get_portfolio(portfolio.id, user1_id)
    assert retrieved.workspace_id == workspace1.id
    
    # User2 cannot access portfolio in workspace1
    with pytest.raises(ValueError):
        await get_portfolio(portfolio.id, user2_id)

@pytest.mark.asyncio
async def test_portfolio_api_data_transformation():
    """Test data transformation between service and API layers"""
    user_id = await create_test_user("transform_test_user")
    workspace = await create_test_workspace(user_id, "Transform Test Workspace")
    
    from services.portfolio_service import create_portfolio, get_portfolio_positions
    
    # Create portfolio with position
    portfolio = await create_portfolio(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Transform Test Portfolio",
        initial_cash=Decimal('10000.00')
    )
    
    # Create a test position directly
    async with get_async_session_context() as session:
        position = Position(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            quantity=Decimal('10'),
            average_price=Decimal('150.00'),
            current_price=Decimal('155.00'),
            opened_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(position)
        await session.commit()
        await session.refresh(position)
    
    # Test service layer returns correct data types
    positions = await get_portfolio_positions(portfolio.id, user_id)
    assert len(positions) == 1
    assert isinstance(positions[0].quantity, Decimal)
    assert isinstance(positions[0].average_price, Decimal)
    assert positions[0].symbol == "AAPL"
    
    # In API layer, we would convert Decimals to float for JSON serialization
    # This would be handled by Pydantic models automatically

@pytest.mark.asyncio
async def test_portfolio_api_pagination_and_sorting():
    """Test pagination and sorting functionality"""
    user_id = await create_test_user("pagination_user")
    workspace = await create_test_workspace(user_id, "Pagination Workspace")
    
    from services.portfolio_service import create_portfolio, get_user_portfolios
    from core.plugin import apply_sorting, apply_pagination
    
    # Create multiple portfolios
    portfolios = []
    for i in range(5):
        portfolio = await create_portfolio(
            user_id=user_id,
            workspace_id=workspace.id,
            name=f"Portfolio {i+1}",
            initial_cash=Decimal(f'{(i+1)*1000}.00')
        )
        portfolios.append(portfolio)
    
    # Get all portfolios
    all_portfolios = await get_user_portfolios(user_id, workspace.id)
    assert len(all_portfolios) == 5
    
    # Test sorting by name
    sorted_portfolios = apply_sorting(all_portfolios, "name", "asc")
    assert sorted_portfolios[0].name == "Portfolio 1"
    assert sorted_portfolios[-1].name == "Portfolio 5"
    
    # Test pagination
    paginated = apply_pagination(all_portfolios, page=1, limit=3)
    assert len(paginated["data"]) == 3
    assert paginated["pagination"]["total"] == 5
    assert paginated["pagination"]["page"] == 1
    assert paginated["pagination"]["limit"] == 3
    
    # Test second page
    paginated_page2 = apply_pagination(all_portfolios, page=2, limit=3)
    assert len(paginated_page2["data"]) == 2  # Remaining items
    assert paginated_page2["pagination"]["page"] == 2

@pytest.mark.asyncio
async def test_portfolio_api_model_validation():
    """Test that API models properly validate data"""
    from models.portfolio_models import (
        PortfolioCreateRequest, TradeSimulationRequest,
        PortfolioResponse, PositionResponse
    )
    from pydantic import ValidationError
    
    # Test valid portfolio creation request
    valid_request = PortfolioCreateRequest(
        name="Test Portfolio",
        description="A test portfolio",
        initial_cash=Decimal('5000.00')
    )
    assert valid_request.name == "Test Portfolio"
    assert valid_request.initial_cash == Decimal('5000.00')
    
    # Test invalid portfolio creation request (negative cash)
    with pytest.raises(ValidationError):
        PortfolioCreateRequest(
            name="Invalid Portfolio",
            initial_cash=Decimal('-1000.00')  # Should fail validation
        )
    
    # Test valid trade simulation request
    valid_trade = TradeSimulationRequest(
        symbol="AAPL",
        quantity=Decimal('10'),
        price=Decimal('150.00'),
        trade_type="buy"
    )
    assert valid_trade.symbol == "AAPL"
    assert valid_trade.trade_type == "buy"
    
    # Test invalid trade simulation request (zero quantity)
    with pytest.raises(ValidationError):
        TradeSimulationRequest(
            symbol="AAPL",
            quantity=Decimal('0'),  # Should fail validation (must be > 0)
            price=Decimal('150.00'),
            trade_type="buy"
        )
    
    # Test response model creation
    portfolio_response = PortfolioResponse(
        id=1,
        name="Test Portfolio",
        description="Test description",
        created_by=1,
        workspace_id=1,
        initial_cash=Decimal('10000.00'),
        current_cash=Decimal('9500.00'),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        position_count=2
    )
    
    assert portfolio_response.id == 1
    assert portfolio_response.position_count == 2
    
    # Test position response with calculated fields
    position_response = PositionResponse(
        id=1,
        symbol="AAPL",
        quantity=Decimal('10'),
        average_price=Decimal('150.00'),
        current_price=Decimal('155.00'),
        position_type="long",
        opened_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        market_value=Decimal('1550.00'),
        unrealized_pnl=Decimal('50.00'),
        unrealized_pnl_percentage=Decimal('3.33')
    )
    
    assert position_response.symbol == "AAPL"
    assert position_response.market_value == Decimal('1550.00')
    assert position_response.unrealized_pnl == Decimal('50.00')

# Integration test with mocked FastAPI dependencies would go here
# This would require setting up TestClient and mocking authentication
# For now, the service integration tests above provide good coverage