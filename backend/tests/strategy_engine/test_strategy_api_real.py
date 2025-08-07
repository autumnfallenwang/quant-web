# tests/strategy_engine/test_strategy_api_real.py
"""
Real API endpoint tests using FastAPI TestClient
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from core.init import run_all

# We need to create a test app with the strategy router
from fastapi import FastAPI
from api.strategy import router as strategy_router

# Create test app
app = FastAPI()
app.include_router(strategy_router)

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup database once for all tests"""
    run_all()


def test_strategy_api_import_works():
    """Test that the strategy API can be imported without errors"""
    from api.strategy import router
    assert router is not None
    
    # Check that we can create a test client
    test_app = FastAPI()
    test_app.include_router(router)
    test_client = TestClient(test_app)
    assert test_client is not None


def test_list_strategies_endpoint():
    """Test the list strategies endpoint actually works"""
    
    # Mock the dependency
    def mock_get_current_user():
        mock_user = MagicMock()
        mock_user.id = 1
        return mock_user
    
    # Override the dependency
    from api.strategy import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    # Mock service response
    mock_strategy = MagicMock()
    mock_strategy.id = 1
    mock_strategy.name = "Test Strategy"
    mock_strategy.strategy_type = "momentum"
    mock_strategy.workspace_id = 1
    mock_strategy.created_by = 1
    mock_strategy.model_dump.return_value = {
        "id": 1,
        "name": "Test Strategy",
        "description": None,
        "strategy_type": "momentum",
        "strategy_code": None,
        "is_active": True,
        "is_public": False,
        "risk_level": "medium",
        "workspace_id": 1,
        "created_by": 1,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    # Mock service functions
    with patch('api.strategy.get_user_strategies') as mock_get_strategies, \
         patch('api.strategy.get_strategy_parameters') as mock_get_params:
        
        mock_get_strategies.return_value = [mock_strategy]
        mock_get_params.return_value = []
        
        try:
            # Make API call
            response = client.get("/workspace/1/strategies")
            
            # Check response
            assert response.status_code == 200
            data = response.json()
            assert "strategies" in data
            assert "total_count" in data
            assert data["total_count"] == 1
            assert len(data["strategies"]) == 1
            assert data["strategies"][0]["name"] == "Test Strategy"
            
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()


@patch('api.strategy.get_current_user')
def test_create_strategy_endpoint(mock_get_current_user):
    """Test the create strategy endpoint"""
    
    # Mock user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_get_current_user.return_value = mock_user
    
    # Mock service function
    with patch('api.strategy.create_strategy') as mock_create:
        mock_strategy = MagicMock()
        mock_strategy.id = 1
        mock_strategy.name = "New Strategy"
        mock_strategy.model_dump.return_value = {
            "id": 1,
            "name": "New Strategy",
            "description": "Test description",
            "strategy_type": "momentum",
            "strategy_code": None,
            "is_active": True,
            "is_public": False,
            "risk_level": "medium",
            "workspace_id": 1,
            "created_by": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
        mock_create.return_value = mock_strategy
        
        # Mock get_strategy_parameters
        with patch('api.strategy.get_strategy_parameters') as mock_get_params:
            mock_get_params.return_value = []
            
            # Prepare request data
            request_data = {
                "name": "New Strategy",
                "strategy_type": "momentum",
                "description": "Test description",
                "risk_level": "medium"
            }
            
            # Make API call
            response = client.post("/workspace/1/strategies", json=request_data)
            
            # Check response
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "New Strategy"
            assert data["strategy_type"] == "momentum"


def test_invalid_strategy_type():
    """Test validation of invalid strategy type"""
    with patch('api.strategy.get_current_user'):
        request_data = {
            "name": "Invalid Strategy",
            "strategy_type": "invalid_type",  # This should fail validation
            "risk_level": "medium"
        }
        
        response = client.post("/workspace/1/strategies", json=request_data)
        
        # Should return 422 for validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


def test_api_routes_exist():
    """Test that all expected routes are registered"""
    routes = [route.path for route in app.routes]
    
    expected_routes = [
        "/workspace/{workspace_id}/strategies",
        "/workspace/{workspace_id}/strategies/{strategy_id}",
        "/workspace/{workspace_id}/strategies/{strategy_id}/parameters",
        "/workspace/{workspace_id}/strategies/{strategy_id}/parameters/{parameter_name}",
        "/workspace/{workspace_id}/strategies/{strategy_id}/analyze",
        "/workspace/{workspace_id}/strategies/{strategy_id}/backtest",
        "/workspace/{workspace_id}/strategies/{strategy_id}/signals/generate",
        "/workspace/{workspace_id}/strategies/{strategy_id}/signals",
        "/workspace/{workspace_id}/strategies/{strategy_id}/performance",
        "/workspace/{workspace_id}/strategies/{strategy_id}/validate",
        "/workspace/{workspace_id}/strategies/{strategy_id}/clone",
        "/strategies/public"
    ]
    
    for expected_route in expected_routes:
        assert expected_route in routes, f"Route {expected_route} not found in registered routes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])