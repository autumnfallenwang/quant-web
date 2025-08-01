# tests/api/test_data_api.py - Data infrastructure API tests
"""
Test suite for data infrastructure API endpoints.
Tests symbol management, data refresh, and coverage monitoring.
"""
# Standard library imports
import pytest
from unittest.mock import Mock, patch, AsyncMock

# Third-party imports
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Local imports
from main import app
from services.data_service import DataService


class TestDataSymbolsAPI:
    """Test symbol management endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_get_symbols_all(self):
        """Test getting all tracked symbols"""
        with patch.object(DataService, 'get_tracked_symbols') as mock_get:
            mock_get.return_value = {
                "stocks": ["AAPL", "GOOGL", "MSFT"],
                "crypto": ["BTC-USD", "ETH-USD"],
                "total": 5
            }
            
            response = self.client.get("/data/symbols")
            
            assert response.status_code == 200
            data = response.json()
            assert "stocks" in data
            assert "crypto" in data
            assert data["total"] == 5
            assert len(data["stocks"]) == 3
            assert len(data["crypto"]) == 2
    
    def test_get_symbols_filtered_stocks(self):
        """Test getting only stock symbols"""
        with patch.object(DataService, 'get_tracked_symbols') as mock_get:
            mock_get.return_value = {
                "stocks": ["AAPL", "GOOGL", "MSFT"],
                "crypto": ["BTC-USD", "ETH-USD"],
                "total": 5
            }
            
            response = self.client.get("/data/symbols?asset_type=stocks")
            
            assert response.status_code == 200
            data = response.json()
            assert "stocks" in data
            assert "crypto" not in data
            assert data["total"] == 3
    
    def test_get_symbols_filtered_crypto(self):
        """Test getting only crypto symbols"""
        with patch.object(DataService, 'get_tracked_symbols') as mock_get:
            mock_get.return_value = {
                "stocks": ["AAPL", "GOOGL", "MSFT"],
                "crypto": ["BTC-USD", "ETH-USD"],
                "total": 5
            }
            
            response = self.client.get("/data/symbols?asset_type=crypto")
            
            assert response.status_code == 200
            data = response.json()
            assert "crypto" in data
            assert "stocks" not in data
            assert data["total"] == 2
    
    def test_add_symbol_auto_detect_stock(self):
        """Test adding stock symbol with auto-detection"""
        with patch.object(DataService, 'add_symbol') as mock_add:
            response = self.client.post("/data/symbols", json={"symbol": "NVDA", "asset_type": "auto"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "NVDA"
            assert data["asset_type"] == "stock"
            assert "added successfully" in data["message"]
            mock_add.assert_called_once_with("NVDA", "auto")
    
    def test_add_symbol_auto_detect_crypto(self):
        """Test adding crypto symbol with auto-detection"""
        with patch.object(DataService, 'add_symbol') as mock_add:
            response = self.client.post("/data/symbols", json={"symbol": "SOL-USD", "asset_type": "auto"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "SOL-USD"
            assert data["asset_type"] == "crypto"
            assert "added successfully" in data["message"]
            mock_add.assert_called_once_with("SOL-USD", "auto")
    
    def test_add_symbol_explicit_type(self):
        """Test adding symbol with explicit type"""
        with patch.object(DataService, 'add_symbol') as mock_add:
            response = self.client.post("/data/symbols", json={"symbol": "TSLA", "asset_type": "stock"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "TSLA"
            assert data["asset_type"] == "stock"
            mock_add.assert_called_once_with("TSLA", "stock")
    
    def test_add_symbol_error_handling(self):
        """Test add symbol error handling"""
        with patch.object(DataService, 'add_symbol') as mock_add:
            mock_add.side_effect = ValueError("Invalid symbol format")
            
            response = self.client.post("/data/symbols", json={"symbol": "INVALID"})
            
            assert response.status_code == 400
            assert "Invalid symbol format" in response.json()["detail"]
    
    def test_remove_symbol_success(self):
        """Test successful symbol removal"""
        with patch.object(DataService, 'remove_symbol') as mock_remove:
            response = self.client.delete("/data/symbols/NVDA")
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "NVDA"
            assert "removed successfully" in data["message"]
            mock_remove.assert_called_once_with("NVDA")
    
    def test_remove_symbol_error_handling(self):
        """Test remove symbol error handling"""
        with patch.object(DataService, 'remove_symbol') as mock_remove:
            mock_remove.side_effect = ValueError("Symbol not found")
            
            response = self.client.delete("/data/symbols/NONEXISTENT")
            
            assert response.status_code == 400
            assert "Symbol not found" in response.json()["detail"]


class TestDataRefreshAPI:
    """Test data refresh endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_refresh_data_async_all(self):
        """Test async refresh for all symbols"""
        with patch.object(DataService, 'get_tracked_symbols') as mock_get:
            mock_get.return_value = {"total": 70}
            
            response = self.client.post("/data/refresh", json={
                "days_back": 30,
                "asset_type": "all", 
                "async_mode": True
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "background" in data["message"]
            assert data["symbols_count"] == 70
            assert "140 seconds" in data["estimated_duration"]
    
    def test_refresh_data_sync_stocks(self):
        """Test synchronous refresh for stocks only"""
        mock_result = {
            "success": [{"symbol": "AAPL", "rows": 126}],
            "failed": [],
            "summary": {"successful": 1, "failed": 0, "success_rate": 100.0}
        }
        
        with patch.object(DataService, 'refresh_sp500_only') as mock_refresh:
            mock_refresh.return_value = mock_result
            
            response = self.client.post("/data/refresh", json={
                "asset_type": "stocks",
                "async_mode": False
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["result"]["summary"]["successful"] == 1
            mock_refresh.assert_called_once_with(30)  # default days_back
    
    def test_refresh_data_sync_crypto(self):
        """Test synchronous refresh for crypto only"""
        mock_result = {
            "success": [{"symbol": "BTC-USD", "rows": 126}],
            "failed": [],
            "summary": {"successful": 1, "failed": 0, "success_rate": 100.0}
        }
        
        with patch.object(DataService, 'refresh_crypto_only') as mock_refresh:
            mock_refresh.return_value = mock_result
            
            response = self.client.post("/data/refresh", json={
                "asset_type": "crypto",
                "async_mode": False
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["result"]["summary"]["successful"] == 1
            mock_refresh.assert_called_once_with(30)  # default days_back
    
    def test_refresh_data_sync_all(self):
        """Test synchronous refresh for all symbols"""
        mock_result = {
            "success": [{"symbol": "AAPL", "rows": 126}],
            "failed": [],
            "summary": {"successful": 1, "failed": 0, "success_rate": 100.0}
        }
        
        with patch.object(DataService, 'refresh_all_symbols') as mock_refresh:
            mock_refresh.return_value = mock_result
            
            response = self.client.post("/data/refresh", json={
                "days_back": 7,
                "interval": "1h",
                "async_mode": False
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            mock_refresh.assert_called_once_with(7, "1h")
    
    def test_refresh_data_error_handling(self):
        """Test refresh error handling"""
        with patch.object(DataService, 'refresh_all_symbols') as mock_refresh:
            mock_refresh.side_effect = Exception("Network timeout")
            
            response = self.client.post("/data/refresh", json={"async_mode": False})
            
            assert response.status_code == 500
            assert "Network timeout" in response.json()["detail"]
    
    def test_refresh_data_validation(self):
        """Test request validation"""
        # Test invalid days_back
        response = self.client.post("/data/refresh", json={"days_back": 500})
        assert response.status_code == 422
        
        # Test invalid interval
        response = self.client.post("/data/refresh", json={"interval": "5m"})
        assert response.status_code == 422
        
        # Test invalid asset_type
        response = self.client.post("/data/refresh", json={"asset_type": "bonds"})
        assert response.status_code == 422


class TestDataCoverageAPI:
    """Test data coverage endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_get_coverage_all_symbols(self):
        """Test getting coverage for all symbols"""
        mock_coverage = {
            "stocks": {
                "AAPL": {
                    "raw": {"earliest": "2024-01-01", "latest": "2024-06-30", "file_count": 1},
                    "processed": {"earliest": "2024-01-01", "latest": "2024-06-30", "file_count": 1},
                    "cache": {"earliest": "2024-03-01", "latest": "2024-03-31", "file_count": 2}
                }
            },
            "crypto": {},
            "total_symbols": 1,
            "coverage_stats": {"full_coverage": 1, "partial_coverage": 0, "no_coverage": 0}
        }
        
        with patch.object(DataService, 'get_data_coverage_summary') as mock_coverage_fn:
            mock_coverage_fn.return_value = mock_coverage
            
            response = self.client.get("/data/coverage")
            
            assert response.status_code == 200
            data = response.json()
            assert "stocks" in data
            assert "coverage_stats" in data
            assert data["total_symbols"] == 1
            assert data["coverage_stats"]["full_coverage"] == 1
    
    def test_get_coverage_specific_symbol(self):
        """Test getting coverage for specific symbol"""
        mock_coverage = {
            "raw": {"earliest": "2024-01-01", "latest": "2024-06-30", "file_count": 1},
            "processed": {"earliest": "2024-01-01", "latest": "2024-06-30", "file_count": 1},
            "cache": {"earliest": "2024-03-01", "latest": "2024-03-31", "file_count": 2}
        }
        
        with patch('core.data_engine.DataEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine.get_data_coverage.return_value = mock_coverage
            mock_engine_class.return_value = mock_engine
            
            response = self.client.get("/data/coverage?symbol=AAPL")
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert "coverage" in data
            assert data["coverage"]["raw"]["file_count"] == 1
            mock_engine.get_data_coverage.assert_called_once_with("AAPL", "1d")
    
    def test_get_coverage_error_handling(self):
        """Test coverage error handling"""
        with patch.object(DataService, 'get_data_coverage_summary') as mock_coverage:
            mock_coverage.side_effect = Exception("Database error")
            
            response = self.client.get("/data/coverage")
            
            assert response.status_code == 500
            assert "Database error" in response.json()["detail"]


class TestScheduledRefreshAPI:
    """Test scheduled refresh endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_daily_refresh(self):
        """Test daily refresh endpoint"""
        response = self.client.post("/data/refresh/daily")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "Daily refresh" in data["message"]
        assert data["schedule"] == "Last 7 days"
    
    def test_weekly_refresh(self):
        """Test weekly refresh endpoint"""
        response = self.client.post("/data/refresh/weekly")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "Weekly refresh" in data["message"]
        assert data["schedule"] == "Last 30 days"
    
    def test_monthly_refresh(self):
        """Test monthly refresh endpoint"""
        response = self.client.post("/data/refresh/monthly")
        
        assert response.status_code == 200
        data = response.json() 
        assert data["status"] == "started"
        assert "Monthly refresh" in data["message"]
        assert data["schedule"] == "Last 90 days"


class TestDataAPIIntegration:
    """Integration tests for data API workflows"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_full_symbol_management_workflow(self):
        """Test complete symbol management workflow"""
        # Mock service methods
        with patch.object(DataService, 'get_tracked_symbols') as mock_get, \
             patch.object(DataService, 'add_symbol') as mock_add, \
             patch.object(DataService, 'remove_symbol') as mock_remove:
            
            # Initial state
            mock_get.return_value = {"stocks": ["AAPL"], "crypto": ["BTC-USD"], "total": 2}
            
            # Get initial symbols
            response = self.client.get("/data/symbols")
            assert response.status_code == 200
            assert response.json()["total"] == 2
            
            # Add new symbol
            response = self.client.post("/data/symbols", json={"symbol": "NVDA"})
            assert response.status_code == 200
            assert response.json()["symbol"] == "NVDA"
            
            # Remove symbol
            response = self.client.delete("/data/symbols/NVDA")
            assert response.status_code == 200
            assert response.json()["symbol"] == "NVDA"
            
            # Verify calls
            mock_add.assert_called_once_with("NVDA", "auto")
            mock_remove.assert_called_once_with("NVDA")
    
    def test_refresh_and_coverage_workflow(self):
        """Test refresh followed by coverage check"""
        with patch.object(DataService, 'refresh_all_symbols') as mock_refresh, \
             patch.object(DataService, 'get_data_coverage_summary') as mock_coverage:
            
            # Mock refresh result
            mock_refresh.return_value = {
                "summary": {"successful": 1, "failed": 0}
            }
            
            # Mock coverage result
            mock_coverage.return_value = {
                "coverage_stats": {"full_coverage": 1, "no_coverage": 0}
            }
            
            # Trigger refresh
            response = self.client.post("/data/refresh", json={"async_mode": False})
            assert response.status_code == 200
            assert response.json()["status"] == "completed"
            
            # Check coverage
            response = self.client.get("/data/coverage")
            assert response.status_code == 200
            assert response.json()["coverage_stats"]["full_coverage"] == 1


@pytest.fixture
def cleanup_test_data():
    """Fixture to clean up test data after tests"""
    yield
    # Cleanup logic here - for now just pass since we're using mocks
    pass


def test_api_endpoints_registered():
    """Test that all API endpoints are properly registered"""
    client = TestClient(app)
    
    # Test endpoints exist (will return 422 for missing params, not 404)
    response = client.get("/data/symbols")
    assert response.status_code != 404
    
    response = client.post("/data/symbols")
    assert response.status_code != 404  # Will be 422 for missing query params
    
    response = client.post("/data/refresh")
    assert response.status_code != 404
    
    response = client.get("/data/coverage")
    assert response.status_code != 404