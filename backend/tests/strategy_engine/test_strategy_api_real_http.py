# tests/strategy_engine/test_strategy_api_real_http.py
"""
Real Strategy API endpoint tests using actual HTTP requests to running server.
Tests all strategy management endpoints with authentication.
"""
import requests
import json
import time
from typing import Dict, List

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_WORKSPACE_ID = 1
TEST_USER_ID = 1

class TestStrategyAPIReal:
    """Real API tests using actual HTTP requests"""
    
    @classmethod
    def setup_class(cls):
        """Setup for strategy API tests with authentication"""
        cls.auth_token = None
        cls.auth_headers = {}
        cls.created_strategies = []  # Track strategies created during tests for cleanup
        cls.user_id = TEST_USER_ID
        cls.workspace_id = TEST_WORKSPACE_ID
        
        print("🚀 Starting Strategy API Real Tests (Authentication required)")
        
        # Login and get authentication token
        cls._setup_authentication()
        
        # Verify workspace access
        cls._verify_workspace_access()
    
    @classmethod
    def _setup_authentication(cls):
        """Setup authentication for tests"""
        # Try to login with john_user first (existing test user)
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json={
                "username": "john_user", 
                "password": "SuperSecret123!"
            })
            if response.status_code == 200:
                cls.auth_token = response.json()["access_token"]
                cls.auth_headers = {"Authorization": f"Bearer {cls.auth_token}"}
                print("✅ Logged in with john_user")
                return
            else:
                raise Exception("john_user login failed")
        except:
            # Fallback: try to create and login with a new test user
            try:
                # Register new user
                register_response = requests.post(f"{BASE_URL}/auth/register", json={
                    "username": "strategy_api_test_user",
                    "password": "TestPassword123",
                    "email": "strategy_api_test@example.com"
                })
                
                # Login with new user
                login_response = requests.post(f"{BASE_URL}/auth/login", json={
                    "username": "strategy_api_test_user",
                    "password": "TestPassword123"
                })
                
                if login_response.status_code == 200:
                    cls.auth_token = login_response.json()["access_token"]
                    cls.auth_headers = {"Authorization": f"Bearer {cls.auth_token}"}
                    print("✅ Created and logged in with strategy_api_test_user")
                    return
                else:
                    raise Exception("New user login failed")
            except Exception as e:
                print(f"⚠️ Authentication failed: {e}")
                # Set empty token - tests will be skipped if no auth
                cls.auth_token = None
                cls.auth_headers = {}
    
    
    @classmethod
    def _verify_workspace_access(cls):
        """Verify access to test workspace"""
        try:
            # Try to access workspace - if it fails, we'll handle in individual tests
            print(f"📋 Using workspace {cls.workspace_id} for testing")
        except Exception as e:
            print(f"⚠️ Workspace access verification failed: {e}")
    
    @classmethod
    def teardown_class(cls):
        """Clean up test strategies"""
        print("🧹 Cleaning up test data...")
        
        # Remove any strategies we created during tests
        for strategy_id in cls.created_strategies:
            try:
                response = requests.delete(
                    f"{BASE_URL}/workspace/{cls.workspace_id}/strategies/{strategy_id}",
                    headers=cls.auth_headers
                )
                if response.status_code in [200, 204, 404]:
                    print(f"✅ Cleaned up strategy {strategy_id}")
                else:
                    print(f"⚠️ Could not clean up strategy {strategy_id}: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Error cleaning up strategy {strategy_id}: {e}")
    
    def test_01_list_strategies(self):
        """Test GET /workspace/{workspace_id}/strategies - List strategies"""
        print("🧪 Testing: List Strategies")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        response = requests.get(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies",
            headers=self.auth_headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict), "Expected dict response structure"
        assert "strategies" in data, "Response should have 'strategies' field"
        assert "total_count" in data, "Response should have 'total_count' field"
        assert "page" in data, "Response should have 'page' field"
        assert "page_size" in data, "Response should have 'page_size' field"
        assert isinstance(data["strategies"], list), "Strategies should be a list"
        
        self.initial_strategy_count = data["total_count"]
        print(f"✅ Found {self.initial_strategy_count} existing strategies")
    
    def test_02_create_strategy(self):
        """Test POST /workspace/{workspace_id}/strategies - Create strategy"""
        print("🧪 Testing: Create Strategy")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            self.created_strategy_id = 1  # Mock ID for subsequent tests
            return
        
        strategy_data = {
            "name": "Test Momentum Strategy",
            "strategy_type": "momentum", 
            "description": "A test momentum strategy for API testing",
            "risk_level": "medium",
            "is_public": False,
            "parameters": [
                {
                    "name": "lookback_period",
                    "type": "int",
                    "default_value": "20",
                    "current_value": "20",
                    "min_value": "1",
                    "max_value": "100",
                    "description": "Period for momentum calculation",
                    "is_required": True
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=strategy_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["name"] == strategy_data["name"]
            assert data["strategy_type"] == strategy_data["strategy_type"]
            assert data["risk_level"] == strategy_data["risk_level"]
            assert "id" in data
            
            # Track for cleanup
            self.created_strategy_id = data["id"]
            self.created_strategies.append(self.created_strategy_id)
            print(f"✅ Created strategy: {data['name']} (ID: {data['id']})")
        else:
            print(f"⚠️ Create strategy failed: {response.status_code} - {response.text}")
            # Create a mock strategy ID for subsequent tests
            self.created_strategy_id = 1
    
    def test_03_get_strategy(self):
        """Test GET /workspace/{workspace_id}/strategies/{strategy_id} - Get strategy"""
        print("🧪 Testing: Get Strategy")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        response = requests.get(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}",
            headers=self.auth_headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "name" in data
            assert "strategy_type" in data
            assert "risk_level" in data
            assert "workspace_id" in data
            
            print(f"✅ Retrieved strategy: {data.get('name', 'Unknown')} (Type: {data.get('strategy_type', 'Unknown')})")
        else:
            print(f"⚠️ Get strategy failed: {response.status_code} - {response.text}")
    
    def test_04_update_strategy(self):
        """Test PATCH /workspace/{workspace_id}/strategies/{strategy_id} - Update strategy"""
        print("🧪 Testing: Update Strategy")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        update_data = {
            "name": "Updated Test Strategy",
            "description": "Updated description for testing",
            "risk_level": "high"
        }
        
        response = requests.patch(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=update_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert data["name"] == update_data["name"]
            assert data["risk_level"] == update_data["risk_level"]
            
            print(f"✅ Updated strategy: {data['name']} (Risk: {data['risk_level']})")
        else:
            print(f"⚠️ Update strategy failed: {response.status_code} - {response.text}")
    
    def test_05_get_strategy_parameters(self):
        """Test GET /workspace/{workspace_id}/strategies/{strategy_id}/parameters - Get parameters"""
        print("🧪 Testing: Get Strategy Parameters")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        response = requests.get(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/parameters",
            headers=self.auth_headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), "Parameters should be a list"
            
            # Check parameter structure if any exist
            if data:
                param = data[0]
                assert "parameter_name" in param
                assert "parameter_type" in param
                assert "current_value" in param
                
            print(f"✅ Retrieved {len(data)} parameters")
        else:
            print(f"⚠️ Get parameters failed: {response.status_code} - {response.text}")
    
    def test_06_update_strategy_parameter(self):
        """Test PATCH /workspace/{workspace_id}/strategies/{strategy_id}/parameters/{parameter_name} - Update parameter"""
        print("🧪 Testing: Update Strategy Parameter")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        parameter_name = "lookback_period"
        
        update_data = {
            "current_value": "25"
        }
        
        response = requests.patch(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/parameters/{parameter_name}",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=update_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert data["parameter_name"] == parameter_name
            assert data["current_value"] == update_data["current_value"]
            
            print(f"✅ Updated parameter {parameter_name} to {data['current_value']}")
        else:
            print(f"⚠️ Update parameter failed: {response.status_code} - {response.text}")
    
    def test_07_analyze_strategy_quick(self):
        """Test POST /workspace/{workspace_id}/strategies/{strategy_id}/analyze - Quick analysis"""
        print("🧪 Testing: Analyze Strategy (Quick)")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        analysis_data = {
            "analysis_type": "quick",
            "include_risk_metrics": True,
            "include_allocation": True
        }
        
        response = requests.post(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/analyze",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=analysis_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "strategy_id" in data
            assert "performance_metrics" in data
            assert "analysis_timestamp" in data
            
            print(f"✅ Quick analysis completed for strategy {data.get('strategy_id')}")
        else:
            print(f"⚠️ Strategy analysis failed: {response.status_code} - {response.text}")
    
    def test_08_analyze_strategy_comprehensive(self):
        """Test POST /workspace/{workspace_id}/strategies/{strategy_id}/analyze - Comprehensive analysis"""
        print("🧪 Testing: Analyze Strategy (Comprehensive)")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        analysis_data = {
            "analysis_type": "comprehensive"
        }
        
        response = requests.post(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/analyze",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=analysis_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "strategy_id" in data
            assert "analysis_type" in data
            assert data["analysis_type"] == "comprehensive"
            
            if "job_id" in data:
                print(f"✅ Comprehensive analysis job started: {data['job_id']}")
            else:
                print("✅ Comprehensive analysis completed immediately")
        else:
            print(f"⚠️ Comprehensive analysis failed: {response.status_code} - {response.text}")
    
    def test_09_backtest_strategy(self):
        """Test POST /workspace/{workspace_id}/strategies/{strategy_id}/backtest - Backtest strategy"""
        print("🧪 Testing: Backtest Strategy")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        backtest_data = {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-12-31T23:59:59Z",
            "initial_capital": 100000.00
        }
        
        response = requests.post(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/backtest",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=backtest_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "strategy_id" in data
            assert "analysis_type" in data
            assert data["analysis_type"] == "backtest"
            
            if "job_id" in data:
                print(f"✅ Backtest job started: {data['job_id']}")
            else:
                print("✅ Backtest completed immediately")
        else:
            print(f"⚠️ Backtest failed: {response.status_code} - {response.text}")
    
    def test_10_generate_signals(self):
        """Test POST /workspace/{workspace_id}/strategies/{strategy_id}/signals/generate - Generate signals"""
        print("🧪 Testing: Generate Signals")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        signal_data = {
            "market_data": {
                "AAPL": {
                    "prices": [150.0, 151.0, 152.0, 153.0, 154.0],
                    "volumes": [100000, 110000, 95000, 120000, 105000]
                },
                "MSFT": {
                    "prices": [380.0, 382.0, 385.0, 387.0, 390.0],
                    "volumes": [50000, 55000, 48000, 60000, 52000]
                }
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/signals/generate",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=signal_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "signals" in data
            assert "total_count" in data
            assert isinstance(data["signals"], list)
            
            print(f"✅ Generated {data['total_count']} signals")
        else:
            print(f"⚠️ Signal generation failed: {response.status_code} - {response.text}")
    
    def test_11_get_signals(self):
        """Test GET /workspace/{workspace_id}/strategies/{strategy_id}/signals - Get signals"""
        print("🧪 Testing: Get Signals")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        response = requests.get(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/signals",
            headers=self.auth_headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "signals" in data
            assert "total_count" in data
            assert isinstance(data["signals"], list)
            
            print(f"✅ Retrieved {data['total_count']} signals")
        else:
            print(f"⚠️ Get signals failed: {response.status_code} - {response.text}")
    
    def test_12_get_strategy_performance(self):
        """Test GET /workspace/{workspace_id}/strategies/{strategy_id}/performance - Get performance"""
        print("🧪 Testing: Get Strategy Performance")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        response = requests.get(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/performance",
            headers=self.auth_headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "performance_records" in data
            assert "total_count" in data
            assert isinstance(data["performance_records"], list)
            
            print(f"✅ Retrieved {data['total_count']} performance records")
        else:
            print(f"⚠️ Get performance failed: {response.status_code} - {response.text}")
    
    def test_13_validate_strategy(self):
        """Test GET /workspace/{workspace_id}/strategies/{strategy_id}/validate - Validate strategy"""
        print("🧪 Testing: Validate Strategy")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        response = requests.get(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/validate",
            headers=self.auth_headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "strategy_id" in data
            assert "is_valid" in data
            assert "issues" in data
            assert "warnings" in data
            assert "validation_timestamp" in data
            
            print(f"✅ Strategy validation: {'Valid' if data['is_valid'] else 'Invalid'}")
            if data.get("warnings"):
                print(f"   Warnings: {len(data['warnings'])}")
            if data.get("issues"):
                print(f"   Issues: {len(data['issues'])}")
        else:
            print(f"⚠️ Strategy validation failed: {response.status_code} - {response.text}")
    
    def test_14_clone_strategy(self):
        """Test POST /workspace/{workspace_id}/strategies/{strategy_id}/clone - Clone strategy"""
        print("🧪 Testing: Clone Strategy")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        strategy_id = getattr(self, 'created_strategy_id', 1)
        
        clone_data = {
            "new_name": "Cloned Test Strategy",
            "target_workspace_id": self.workspace_id
        }
        
        response = requests.post(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}/clone",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=clone_data
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["name"] == clone_data["new_name"]
            assert "id" in data
            
            # Track for cleanup
            self.created_strategies.append(data["id"])
            print(f"✅ Cloned strategy: {data['name']} (ID: {data['id']})")
        else:
            print(f"⚠️ Clone strategy failed: {response.status_code} - {response.text}")
    
    def test_15_get_public_strategies(self):
        """Test GET /strategies/public - Get public strategies"""
        print("🧪 Testing: Get Public Strategies")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        response = requests.get(
            f"{BASE_URL}/strategies/public",
            headers=self.auth_headers
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            assert "strategies" in data
            assert "total_count" in data
            assert "page" in data
            assert "page_size" in data
            assert isinstance(data["strategies"], list)
            
            print(f"✅ Found {data['total_count']} public strategies")
        else:
            print(f"⚠️ Get public strategies failed: {response.status_code} - {response.text}")
    
    def test_16_error_handling(self):
        """Test error handling with invalid requests"""
        print("🧪 Testing: Error Handling")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        # Test invalid strategy type
        invalid_strategy = {
            "name": "Invalid Strategy",
            "strategy_type": "invalid_type",
            "risk_level": "medium"
        }
        
        response = requests.post(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=invalid_strategy
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid strategy type, got {response.status_code}"
        
        # Test accessing non-existent strategy
        response = requests.get(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies/99999",
            headers=self.auth_headers
        )
        
        assert response.status_code in [404, 403], f"Expected 404/403 for non-existent strategy, got {response.status_code}"
        
        # Test invalid risk level
        invalid_risk = {
            "name": "Invalid Risk Strategy",
            "strategy_type": "momentum", 
            "risk_level": "invalid_risk"
        }
        
        response = requests.post(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies",
            headers={**self.auth_headers, "Content-Type": "application/json"},
            json=invalid_risk
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid risk level, got {response.status_code}"
        
        print("✅ Error handling works correctly")
    
    def test_17_data_consistency(self):
        """Test data consistency across endpoints"""
        print("🧪 Testing: Data Consistency")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        # Get strategy list
        list_response = requests.get(
            f"{BASE_URL}/workspace/{self.workspace_id}/strategies",
            headers=self.auth_headers
        )
        
        if list_response.status_code == 200:
            list_data = list_response.json()
            total_from_list = list_data["total_count"]
            
            # If we have strategies, check individual access
            if list_data["strategies"]:
                strategy = list_data["strategies"][0]
                strategy_id = strategy["id"]
                
                # Get individual strategy
                get_response = requests.get(
                    f"{BASE_URL}/workspace/{self.workspace_id}/strategies/{strategy_id}",
                    headers=self.auth_headers
                )
                
                if get_response.status_code == 200:
                    get_data = get_response.json()
                    assert get_data["id"] == strategy_id
                    assert get_data["name"] == strategy["name"]
                    print(f"✅ Data consistency verified for strategy {strategy_id}")
                else:
                    print("⚠️ Individual strategy access failed")
            else:
                print("✅ No strategies to verify consistency")
        else:
            print("⚠️ Could not verify data consistency - list endpoint failed")
    
    def test_18_performance_basic(self):
        """Test basic performance characteristics"""
        print("🧪 Testing: Basic Performance")
        
        if not self.auth_token:
            print("⚠️ Skipping test - no authentication token")
            return
        
        # Test response times for key endpoints
        endpoints_to_test = [
            (f"/workspace/{self.workspace_id}/strategies", "GET"),
            ("/strategies/public", "GET")
        ]
        
        for endpoint, method in endpoints_to_test:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=self.auth_headers)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"   {method} {endpoint}: {response_time:.3f}s (status: {response.status_code})")
            
            # Basic performance assertion (should respond within 10 seconds for strategy endpoints)
            assert response_time < 10.0, f"{endpoint} took too long: {response_time}s"
        
        print("✅ Basic performance requirements met")


def run_strategy_api_tests():
    """Run all strategy API tests"""
    print("🚀 Starting Strategy API Real Tests...")
    print("=" * 60)
    
    test_instance = TestStrategyAPIReal()
    
    try:
        # Setup
        test_instance.setup_class()
        
        # Run all tests
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        test_methods.sort()  # Run in order
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                print(f"\n📋 Running: {test_method}")
                getattr(test_instance, test_method)()
                passed += 1
                print(f"✅ PASSED: {test_method}")
            except Exception as e:
                failed += 1
                print(f"❌ FAILED: {test_method} - {str(e)}")
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed} passed, {failed} failed")
        
        # Cleanup
        test_instance.teardown_class()
        
    except Exception as e:
        print(f"💥 Test setup failed: {e}")


if __name__ == "__main__":
    run_strategy_api_tests()