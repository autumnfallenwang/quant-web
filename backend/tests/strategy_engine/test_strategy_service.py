# tests/strategy_engine/test_strategy_service.py
"""
Tests for the Strategy Service layer
"""
import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlmodel import select

from core.db import get_async_session_context
from core.init import run_all
from models.db_models import (
    Strategy, StrategyParameter, Signal, StrategyPerformance,
    Workspace, WorkspaceMembership, UserProfile, IdentityUser, Job
)
from services.strategy_service import (
    create_strategy, get_strategy, get_user_strategies, update_strategy,
    get_strategy_parameters, update_strategy_parameter, analyze_strategy_quick,
    generate_strategy_signals, get_strategy_signals, validate_strategy_config,
    clone_strategy, get_public_strategies
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


@pytest.mark.asyncio
async def test_create_strategy():
    """Test strategy creation"""
    user_id = await create_test_user("strategy_creator")
    workspace = await create_test_workspace(user_id, "Strategy Workspace")
    
    # Test creating a basic strategy
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Test Momentum Strategy",
        strategy_type="momentum",
        description="A test momentum strategy",
        risk_level="medium"
    )
    
    assert strategy.name == "Test Momentum Strategy"
    assert strategy.strategy_type == "momentum"
    assert strategy.workspace_id == workspace.id
    assert strategy.created_by == user_id
    assert strategy.is_active is True


@pytest.mark.asyncio
async def test_create_strategy_with_parameters():
    """Test strategy creation with parameters"""
    user_id = await create_test_user("strategy_with_params")
    workspace = await create_test_workspace(user_id, "Param Workspace")
    
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
        name="Parameterized Strategy",
        strategy_type="momentum",
        parameters=parameters
    )
    
    # Check that parameters were created
    strategy_params = await get_strategy_parameters(strategy.id, user_id)
    assert len(strategy_params) == 2
    
    lookback_param = next(p for p in strategy_params if p.parameter_name == "lookback_period")
    assert lookback_param.parameter_type == "int"
    assert lookback_param.current_value == "20"
    assert lookback_param.min_value == "1"
    
    threshold_param = next(p for p in strategy_params if p.parameter_name == "momentum_threshold")
    assert threshold_param.parameter_type == "float"
    assert threshold_param.current_value == "0.07"


@pytest.mark.asyncio
async def test_get_strategy():
    """Test getting a strategy by ID"""
    user_id = await create_test_user("strategy_getter")
    workspace = await create_test_workspace(user_id, "Get Workspace")
    
    # Create strategy
    created_strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Retrievable Strategy",
        strategy_type="mean_reversion"
    )
    
    # Get strategy
    retrieved_strategy = await get_strategy(created_strategy.id, user_id)
    
    assert retrieved_strategy.id == created_strategy.id
    assert retrieved_strategy.name == "Retrievable Strategy"
    assert retrieved_strategy.strategy_type == "mean_reversion"


@pytest.mark.asyncio
async def test_get_strategy_access_denied():
    """Test that users can't access strategies they don't have permission for"""
    user1_id = await create_test_user("strategy_owner")
    user2_id = await create_test_user("strategy_outsider")
    workspace = await create_test_workspace(user1_id, "Private Workspace")
    
    # Create strategy as user1
    strategy = await create_strategy(
        user_id=user1_id,
        workspace_id=workspace.id,
        name="Private Strategy",
        strategy_type="momentum"
    )
    
    # Try to access as user2 (should fail)
    with pytest.raises(ValueError, match="Strategy not found or access denied"):
        await get_strategy(strategy.id, user2_id)


@pytest.mark.asyncio
async def test_get_user_strategies():
    """Test getting all strategies for a user"""
    user_id = await create_test_user("multi_strategy_user")
    workspace = await create_test_workspace(user_id, "Multi Strategy Workspace")
    
    # Create multiple strategies
    await create_strategy(user_id, workspace.id, "Strategy 1", "momentum")
    await create_strategy(user_id, workspace.id, "Strategy 2", "mean_reversion")
    await create_strategy(user_id, workspace.id, "Strategy 3", "arbitrage")
    
    # Get all strategies
    all_strategies = await get_user_strategies(user_id, workspace.id)
    assert len(all_strategies) == 3
    
    # Test filtering by strategy type
    momentum_strategies = await get_user_strategies(user_id, workspace.id, strategy_type="momentum")
    assert len(momentum_strategies) == 1
    assert momentum_strategies[0].name == "Strategy 1"


@pytest.mark.asyncio
async def test_update_strategy():
    """Test updating strategy details"""
    user_id = await create_test_user("strategy_updater")
    workspace = await create_test_workspace(user_id, "Update Workspace")
    
    # Create strategy
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Original Name",
        strategy_type="momentum",
        description="Original description"
    )
    
    # Update strategy
    updated_strategy = await update_strategy(
        strategy_id=strategy.id,
        user_id=user_id,
        name="Updated Name",
        description="Updated description",
        risk_level="high"
    )
    
    assert updated_strategy.name == "Updated Name"
    assert updated_strategy.description == "Updated description"
    assert updated_strategy.risk_level == "high"
    assert updated_strategy.updated_at > strategy.updated_at


@pytest.mark.asyncio
async def test_update_strategy_parameter():
    """Test updating strategy parameter values"""
    user_id = await create_test_user("param_updater")
    workspace = await create_test_workspace(user_id, "Param Update Workspace")
    
    parameters = [
        {
            "name": "test_param",
            "type": "float",
            "default_value": "0.05",
            "current_value": "0.05"
        }
    ]
    
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Param Test Strategy",
        strategy_type="momentum",
        parameters=parameters
    )
    
    # Update parameter
    updated_param = await update_strategy_parameter(
        strategy_id=strategy.id,
        user_id=user_id,
        parameter_name="test_param",
        current_value="0.10"
    )
    
    assert updated_param.current_value == "0.10"
    assert updated_param.parameter_name == "test_param"


@pytest.mark.asyncio
async def test_analyze_strategy_quick():
    """Test quick strategy analysis"""
    user_id = await create_test_user("strategy_analyzer")
    workspace = await create_test_workspace(user_id, "Analysis Workspace")
    
    parameters = [
        {
            "name": "lookback_period",
            "type": "int",
            "default_value": "20",
            "current_value": "20"
        }
    ]
    
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Analysis Strategy",
        strategy_type="momentum",
        parameters=parameters
    )
    
    # Perform quick analysis
    analysis = await analyze_strategy_quick(strategy.id, user_id)
    
    assert analysis["strategy_id"] == strategy.id
    assert "risk_metrics" in analysis
    assert "signal_analysis" in analysis
    assert "recommendations" in analysis
    assert isinstance(analysis["recommendations"], list)


@pytest.mark.asyncio
async def test_generate_strategy_signals():
    """Test signal generation"""
    user_id = await create_test_user("signal_generator")
    workspace = await create_test_workspace(user_id, "Signal Workspace")
    
    parameters = [
        {
            "name": "lookback_period",
            "type": "int",
            "default_value": "20",
            "current_value": "20"
        },
        {
            "name": "momentum_threshold",
            "type": "float",
            "default_value": "0.05",
            "current_value": "0.05"
        }
    ]
    
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Signal Strategy",
        strategy_type="momentum",
        parameters=parameters
    )
    
    # Mock market data
    market_data = {
        "AAPL": {
            "prices": [150.0, 151.0, 152.0, 153.0, 154.0, 155.0, 156.0, 157.0, 158.0, 159.0,
                      160.0, 161.0, 162.0, 163.0, 164.0, 165.0, 166.0, 167.0, 168.0, 169.0, 170.0],
            "volumes": [100000] * 21
        }
    }
    
    # Generate signals
    signals = await generate_strategy_signals(strategy.id, user_id, market_data)
    
    assert len(signals) > 0
    assert signals[0]["symbol"] == "AAPL"
    assert signals[0]["signal_type"] in ["buy", "sell", "hold"]
    
    # Check that signals were stored in database
    stored_signals = await get_strategy_signals(strategy.id, user_id)
    assert len(stored_signals) == len(signals)


@pytest.mark.asyncio
async def test_validate_strategy_config():
    """Test strategy configuration validation"""
    user_id = await create_test_user("strategy_validator")
    workspace = await create_test_workspace(user_id, "Validation Workspace")
    
    # Create valid strategy
    strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Valid Strategy",
        strategy_type="momentum"
    )
    
    # Validate configuration
    validation = await validate_strategy_config(strategy.id, user_id)
    
    assert validation["is_valid"] is True
    assert isinstance(validation["issues"], list)
    assert isinstance(validation["warnings"], list)


@pytest.mark.asyncio
async def test_clone_strategy():
    """Test strategy cloning"""
    user_id = await create_test_user("strategy_cloner")
    workspace = await create_test_workspace(user_id, "Clone Workspace")
    
    parameters = [
        {
            "name": "test_param",
            "type": "int",
            "default_value": "10",
            "current_value": "15"
        }
    ]
    
    # Create original strategy
    original_strategy = await create_strategy(
        user_id=user_id,
        workspace_id=workspace.id,
        name="Original Strategy",
        strategy_type="momentum",
        description="Original description",
        parameters=parameters
    )
    
    # Clone strategy
    cloned_strategy = await clone_strategy(
        strategy_id=original_strategy.id,
        user_id=user_id,
        new_name="Cloned Strategy"
    )
    
    assert cloned_strategy.name == "Cloned Strategy"
    assert cloned_strategy.strategy_type == original_strategy.strategy_type
    assert cloned_strategy.is_public is False  # Cloned strategies are private
    assert "Cloned from: Original Strategy" in cloned_strategy.description
    
    # Check that parameters were cloned
    cloned_params = await get_strategy_parameters(cloned_strategy.id, user_id)
    original_params = await get_strategy_parameters(original_strategy.id, user_id)
    
    assert len(cloned_params) == len(original_params)
    assert cloned_params[0].parameter_name == original_params[0].parameter_name
    assert cloned_params[0].current_value == original_params[0].current_value


@pytest.mark.asyncio
async def test_get_public_strategies():
    """Test getting public strategies"""
    user1_id = await create_test_user("public_strategy_creator")
    user2_id = await create_test_user("public_strategy_viewer")
    workspace = await create_test_workspace(user1_id, "Public Workspace")
    
    # Create public strategy
    await create_strategy(
        user_id=user1_id,
        workspace_id=workspace.id,
        name="Public Strategy",
        strategy_type="momentum",
        is_public=True
    )
    
    # Create private strategy (should not appear)
    await create_strategy(
        user_id=user1_id,
        workspace_id=workspace.id,
        name="Private Strategy",
        strategy_type="momentum",
        is_public=False
    )
    
    # Get public strategies as different user
    public_strategies = await get_public_strategies(user2_id)
    
    assert len(public_strategies) == 1
    assert public_strategies[0].name == "Public Strategy"
    assert public_strategies[0].is_public is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])