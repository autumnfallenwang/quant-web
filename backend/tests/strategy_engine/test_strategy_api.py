# tests/strategy_engine/test_strategy_api.py
"""
Comprehensive tests for strategy API endpoints.
Uses real database with proper cleanup and follows established patterns.
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
from models.db_models import (
    Strategy, StrategyParameter, Signal, StrategyPerformance,
    Workspace, WorkspaceMembership, UserProfile, IdentityUser, Job
)

# Import the service functions to test API integration
from services.strategy_service import (
    create_strategy, get_strategy, get_user_strategies,
    analyze_strategy_quick, generate_strategy_signals
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
        # Delete strategy-related data
        signal_result = await session.exec(select(Signal))
        for signal in signal_result.all():
            await session.delete(signal)
        
        perf_result = await session.exec(select(StrategyPerformance))
        for perf in perf_result.all():
            await session.delete(perf)
        
        param_result = await session.exec(select(StrategyParameter))
        for param in param_result.all():
            await session.delete(param)
        
        strategy_result = await session.exec(select(Strategy))
        for strategy in strategy_result.all():
            await session.delete(strategy)
        
        # Delete jobs (they reference workspaces)
        job_result = await session.exec(select(Job))
        for job in job_result.all():
            await session.delete(job)
        
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
        return MagicMock(id=1, username="testuser", email="test@example.com")
    
    return _mock_get_current_user


# ===== STRATEGY API INTEGRATION TESTS =====

@pytest.mark.asyncio
async def test_strategy_api_integration_flow():
    """Test the complete strategy API integration flow"""
    # Create test data
    user_id = await create_test_user("strategy_api_user")
    workspace = await create_test_workspace(user_id, "API Test Workspace")
    
    # Test 1: Create Strategy (simulating API create request)
    parameters = [
        {
            "name": "lookback_period",
            "type": "int",
            "default_value": "20",
            "current_value": "20",
            "min_value": "1",
            "max_value": "100",
            "description": "Lookback period for momentum calculation"
        },
        {
            "name": "momentum_threshold",
            "type": "float",
            "default_value": "0.05",
            "current_value": "0.07",
            "description": "Minimum momentum threshold for signals"
        }
    ]
    
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="API Test Strategy",
        strategy_type="momentum",
        description="Strategy created via API test",
        risk_level="medium",
        parameters=parameters
    )
    
    assert strategy.name == "API Test Strategy"
    assert strategy.strategy_type == "momentum"
    assert strategy.workspace_id == workspace.id
    assert strategy.created_by == user_id
    
    # Test 2: Get Strategy (simulating API get request)
    retrieved_strategy = await get_strategy(strategy.id, user_id)
    assert retrieved_strategy.id == strategy.id
    assert retrieved_strategy.name == "API Test Strategy"
    
    # Test 3: List User Strategies (simulating API list request)
    strategies = await get_user_strategies(user_id, workspace.id)
    assert len(strategies) == 1
    assert strategies[0].id == strategy.id
    
    # Test 4: Strategy Analysis (simulating API analysis request)
    with patch('services.strategy_service.StrategyEngine') as mock_engine_class:
        from unittest.mock import AsyncMock
        
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Mock the async analyze_strategy method
        mock_analysis_result = MagicMock()
        mock_analysis_result.strategy_id = strategy.id
        mock_analysis_result.performance_metrics = {'total_return': Decimal('1000.00')}
        mock_analysis_result.risk_metrics = {'risk_score': Decimal('0.5')}
        mock_analysis_result.signal_analysis = {'total_signals': 0}
        mock_analysis_result.recommendations = ['Test recommendation']
        mock_analysis_result.analysis_timestamp = datetime.now(timezone.utc)
        
        mock_engine.analyze_strategy = AsyncMock(return_value=mock_analysis_result)
        
        analysis = await analyze_strategy_quick(strategy.id, user_id)
        assert analysis['strategy_id'] == strategy.id
        assert 'performance_metrics' in analysis
        assert 'risk_metrics' in analysis
    
    # Test 5: Signal Generation (simulating API signal generation request)
    with patch('services.strategy_service.StrategyEngine') as mock_engine_class:
        from unittest.mock import AsyncMock
        
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Mock the async generate_signals method
        mock_engine.generate_signals = AsyncMock(return_value=[
            {
                'signal_type': 'buy',
                'symbol': 'AAPL',
                'signal_strength': Decimal('0.8'),
                'price': Decimal('150.00'),
                'confidence_score': Decimal('0.75'),
                'signal_data': {
                    'momentum_score': Decimal('12.58'),
                    'rsi': Decimal('65.00')
                },
                'created_at': datetime.now(timezone.utc)
            }
        ])
        
        market_data = {
            "AAPL": {
                "prices": [150.0, 151.0, 152.0, 153.0, 154.0, 155.0, 156.0, 157.0, 158.0, 159.0,
                          160.0, 161.0, 162.0, 163.0, 164.0, 165.0, 166.0, 167.0, 168.0, 169.0, 170.0],
                "volumes": [100000] * 21
            }
        }
        
        signals = await generate_strategy_signals(
            strategy_id=strategy.id,
            user_id=user_id,
            market_data=market_data
        )
        
        assert len(signals) == 1
        assert signals[0]['symbol'] == 'AAPL'
        assert signals[0]['signal_type'] == 'buy'


@pytest.mark.asyncio
async def test_strategy_api_error_handling():
    """Test API error handling scenarios"""
    user_id = await create_test_user("error_test_user")
    workspace = await create_test_workspace(user_id, "Error Test Workspace")
    
    # Test 1: Strategy not found
    with pytest.raises(ValueError, match="Strategy not found or access denied"):
        await get_strategy(999, user_id)
    
    # Test 2: Access denied (different user)
    other_user_id = await create_test_user("other_user")
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Private Strategy",
        strategy_type="momentum"
    )
    
    with pytest.raises(ValueError, match="Strategy not found or access denied"):
        await get_strategy(strategy.id, other_user_id)


@pytest.mark.asyncio
async def test_strategy_api_workspace_validation():
    """Test workspace validation in API endpoints"""
    user1_id = await create_test_user("workspace_user1")
    user2_id = await create_test_user("workspace_user2")
    
    workspace1 = await create_test_workspace(user1_id, "Workspace 1")
    workspace2 = await create_test_workspace(user2_id, "Workspace 2")
    
    # Create strategy in workspace1
    strategy = await create_strategy(
        user_id=user1_id,
        workspace_id=workspace1.id,
        name="Workspace 1 Strategy",
        strategy_type="momentum"
    )
    
    # User1 can access strategy in their workspace
    retrieved = await get_strategy(strategy.id, user1_id)
    assert retrieved.workspace_id == workspace1.id
    
    # User2 cannot access strategy in workspace1
    with pytest.raises(ValueError):
        await get_strategy(strategy.id, user2_id)


@pytest.mark.asyncio
async def test_strategy_api_data_transformation():
    """Test data transformation between service and API layers"""
    user_id = await create_test_user("transform_test_user")
    workspace = await create_test_workspace(user_id, "Transform Test Workspace")
    
    # Create strategy with parameters
    parameters = [
        {
            "name": "test_param",
            "type": "float",
            "default_value": "0.05",
            "current_value": "0.10"
        }
    ]
    
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Transform Test Strategy",
        strategy_type="momentum",
        parameters=parameters
    )
    
    # Create a test signal directly
    async with get_async_session_context() as session:
        signal = Signal(
            strategy_id=strategy.id,
            signal_type="buy",
            symbol="AAPL",
            signal_strength=Decimal('0.8'),
            price=Decimal('150.00'),
            confidence_score=Decimal('0.75'),
            signal_data={"momentum_score": "12.58", "rsi": "65.00"},  # Already converted to strings
            created_at=datetime.now(timezone.utc)
        )
        session.add(signal)
        await session.commit()
        await session.refresh(signal)
    
    # Test service layer returns correct data types
    from services.strategy_service import get_strategy_signals
    signals = await get_strategy_signals(strategy.id, user_id)
    assert len(signals) == 1
    assert isinstance(signals[0].signal_strength, Decimal)
    assert isinstance(signals[0].price, Decimal)
    assert signals[0].symbol == "AAPL"
    
    # In API layer, Pydantic models would handle serialization automatically


@pytest.mark.asyncio
async def test_strategy_api_pagination_and_sorting():
    """Test pagination and sorting functionality"""
    user_id = await create_test_user("pagination_user")
    workspace = await create_test_workspace(user_id, "Pagination Workspace")
    
    from core.plugin import apply_sorting, apply_pagination
    
    # Create multiple strategies
    strategies = []
    for i in range(5):
        strategy = await create_strategy(
            user_id=user_id,
            workspace_id=workspace.id,
            name=f"Strategy {i+1}",
            strategy_type="momentum",
            risk_level="medium"
        )
        strategies.append(strategy)
    
    # Get all strategies
    all_strategies = await get_user_strategies(user_id, workspace.id)
    assert len(all_strategies) == 5
    
    # Test sorting by name
    sorted_strategies = apply_sorting(all_strategies, "name", "asc")
    assert sorted_strategies[0].name == "Strategy 1"
    assert sorted_strategies[-1].name == "Strategy 5"
    
    # Test pagination
    paginated = apply_pagination(all_strategies, page=1, limit=3)
    assert len(paginated["data"]) == 3
    assert paginated["pagination"]["total"] == 5
    assert paginated["pagination"]["page"] == 1
    assert paginated["pagination"]["limit"] == 3
    
    # Test second page
    paginated_page2 = apply_pagination(all_strategies, page=2, limit=3)
    assert len(paginated_page2["data"]) == 2  # Remaining items
    assert paginated_page2["pagination"]["page"] == 2


@pytest.mark.asyncio
async def test_strategy_api_model_validation():
    """Test that API models properly validate data"""
    from models.strategy_models import (
        StrategyCreateRequest, AnalysisRequest, BacktestRequest,
        StrategyResponse, SignalResponse
    )
    from pydantic import ValidationError
    
    # Test valid strategy creation request
    valid_request = StrategyCreateRequest(
        name="Test Strategy",
        strategy_type="momentum",
        description="A test strategy",
        risk_level="medium"
    )
    assert valid_request.name == "Test Strategy"
    assert valid_request.strategy_type == "momentum"
    
    # Test invalid strategy creation request (invalid strategy type)
    with pytest.raises(ValidationError):
        StrategyCreateRequest(
            name="Invalid Strategy",
            strategy_type="invalid_type"  # Should fail validation
        )
    
    # Test invalid risk level
    with pytest.raises(ValidationError):
        StrategyCreateRequest(
            name="Invalid Risk Strategy",
            strategy_type="momentum",
            risk_level="super_high"  # Should fail validation
        )
    
    # Test valid analysis request
    valid_analysis = AnalysisRequest(
        analysis_type="quick",
        include_risk_metrics=True
    )
    assert valid_analysis.analysis_type == "quick"
    
    # Test invalid analysis request
    with pytest.raises(ValidationError):
        AnalysisRequest(
            analysis_type="invalid_type"  # Should fail validation
        )
    
    # Test valid backtest request
    start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
    
    valid_backtest = BacktestRequest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=Decimal('50000.00')
    )
    assert valid_backtest.start_date == start_date
    assert valid_backtest.end_date == end_date
    
    # Test invalid backtest request (end date before start date)
    with pytest.raises(ValidationError):
        BacktestRequest(
            start_date=end_date,
            end_date=start_date,  # Should fail validation
            initial_capital=Decimal('50000.00')
        )
    
    # Test response model creation
    strategy_response = StrategyResponse(
        id=1,
        name="Test Strategy",
        description="Test description",
        strategy_type="momentum",
        strategy_code=None,
        is_active=True,
        is_public=False,
        risk_level="medium",
        workspace_id=1,
        created_by=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        parameter_count=2
    )
    
    assert strategy_response.id == 1
    assert strategy_response.parameter_count == 2
    
    # Test signal response with calculated fields
    signal_response = SignalResponse(
        id=1,
        strategy_id=1,
        signal_type="buy",
        symbol="AAPL",
        signal_strength=Decimal('0.8'),
        price=Decimal('150.00'),
        confidence_score=Decimal('0.75'),
        signal_data={"momentum_score": "12.58"},
        is_executed=False,
        executed_at=None,
        created_at=datetime.now(timezone.utc)
    )
    
    assert signal_response.symbol == "AAPL"
    assert signal_response.signal_strength == Decimal('0.8')
    assert signal_response.is_executed is False


@pytest.mark.asyncio
async def test_strategy_api_comprehensive_workflow():
    """Test comprehensive API workflow"""
    user_id = await create_test_user("workflow_user")
    workspace = await create_test_workspace(user_id, "Workflow Workspace")
    
    # Step 1: Create multiple strategies with different types
    momentum_strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Momentum Strategy",
        strategy_type="momentum",
        parameters=[
            {
                "name": "lookback_period",
                "type": "int",
                "default_value": "20",
                "current_value": "20"
            }
        ]
    )
    
    mean_reversion_strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Mean Reversion Strategy",
        strategy_type="mean_reversion",
        parameters=[
            {
                "name": "bollinger_periods",
                "type": "int",
                "default_value": "20",
                "current_value": "20"
            }
        ]
    )
    
    # Step 2: List strategies and verify filtering works
    all_strategies = await get_user_strategies(user_id, workspace.id)
    assert len(all_strategies) == 2
    
    momentum_strategies = await get_user_strategies(user_id, workspace.id, strategy_type="momentum")
    assert len(momentum_strategies) == 1
    assert momentum_strategies[0].name == "Momentum Strategy"
    
    # Step 3: Analyze strategies
    with patch('services.strategy_service.StrategyEngine') as mock_engine_class:
        from unittest.mock import AsyncMock
        
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Mock the async analyze_strategy method
        mock_analysis_result = MagicMock()
        mock_analysis_result.strategy_id = momentum_strategy.id
        mock_analysis_result.performance_metrics = {'sharpe_ratio': Decimal('1.2')}
        mock_analysis_result.risk_metrics = {'risk_score': Decimal('0.6')}
        mock_analysis_result.signal_analysis = {'signal_quality': 'good'}
        mock_analysis_result.recommendations = ['Consider diversification']
        mock_analysis_result.analysis_timestamp = datetime.now(timezone.utc)
        
        mock_engine.analyze_strategy = AsyncMock(return_value=mock_analysis_result)
        
        momentum_analysis = await analyze_strategy_quick(momentum_strategy.id, user_id)
        assert momentum_analysis['strategy_id'] == momentum_strategy.id
        assert 'recommendations' in momentum_analysis
    
    # Step 4: Generate signals for momentum strategy
    with patch('services.strategy_service.StrategyEngine') as mock_engine_class:
        from unittest.mock import AsyncMock
        
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        
        # Mock the async generate_signals method
        mock_engine.generate_signals = AsyncMock(return_value=[
            {
                'signal_type': 'buy',
                'symbol': 'MSFT',
                'signal_strength': Decimal('0.7'),
                'price': Decimal('380.00'),
                'confidence_score': Decimal('0.8'),
                'signal_data': {
                    'momentum_score': Decimal('8.5'),
                    'rsi': Decimal('45.0')
                },
                'created_at': datetime.now(timezone.utc)
            }
        ])
        
        market_data = {
            "MSFT": {
                "prices": [370.0, 375.0, 380.0, 385.0, 390.0] * 5,  # 25 prices
                "volumes": [50000] * 25
            }
        }
        
        signals = await generate_strategy_signals(
            strategy_id=momentum_strategy.id,
            user_id=user_id,
            market_data=market_data
        )
        
        assert len(signals) == 1
        assert signals[0]['symbol'] == 'MSFT'
    
    print("✅ Comprehensive API workflow test completed successfully")


# Integration test with mocked FastAPI dependencies would go here
# This would require setting up TestClient and mocking authentication
# For now, the service integration tests above provide good coverage

if __name__ == "__main__":
    pytest.main([__file__, "-v"])