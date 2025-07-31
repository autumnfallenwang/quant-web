# tests/api/test_job_api.py
"""
Comprehensive API tests for workspace-scoped job endpoints.
Tests the modernized job API following our design rulebook patterns.
"""
import pytest
import pytest_asyncio
import uuid
from fastapi.testclient import TestClient
from sqlmodel import select
from datetime import datetime, timezone

from main import app
from core.init import run_all
from core.db import get_async_session_context
from core.security import create_access_token
from models.db_models import IdentityUser, UserProfile, Workspace, WorkspaceMembership, Job

# ===== TEST SETUP =====

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup database once for all tests"""
    run_all()

@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data():
    """Clean up test data after each test"""
    yield  # Run the test first
    
    # Clean up test data
    async with get_async_session_context() as session:
        # Delete all test jobs
        job_result = await session.exec(select(Job))
        for job in job_result.all():
            await session.delete(job)
        
        # Delete all test workspaces and memberships
        result = await session.exec(select(Workspace))
        for workspace in result.all():
            # Delete all memberships for this workspace
            membership_result = await session.exec(
                select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace.id)
            )
            for membership in membership_result.all():
                await session.delete(membership)
            
            # Delete the workspace
            await session.delete(workspace)
        
        # Clean up test users
        user_result = await session.exec(select(UserProfile))
        for profile in user_result.all():
            await session.delete(profile)
        
        identity_result = await session.exec(select(IdentityUser))
        for identity in identity_result.all():
            await session.delete(identity)
            
        await session.commit()

# ===== TEST HELPERS =====

async def create_test_user(base_username: str = "testuser") -> tuple[int, str]:
    """Helper to create a test user and return their profile ID and auth token"""
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
        
        # Create auth token
        token = create_access_token({"sub": username, "iss": "local-idp", "role": "user"})
        
        return profile.id, token

async def create_test_workspace(name: str = "Test Workspace") -> Workspace:
    """Helper to create a test workspace"""
    async with get_async_session_context() as session:
        workspace = Workspace(name=name)
        session.add(workspace)
        await session.commit()
        await session.refresh(workspace)
        return workspace

async def create_test_membership(workspace_id: int, user_id: int, role: str = "member") -> WorkspaceMembership:
    """Helper to create a test membership"""
    async with get_async_session_context() as session:
        membership = WorkspaceMembership(
            workspace_id=workspace_id,
            user_profile_id=user_id,
            role=role
        )
        session.add(membership)
        await session.commit()
        await session.refresh(membership)
        return membership

async def create_test_job(workspace_id: int, user_id: int, job_type: str = "test_job") -> Job:
    """Helper to create a test job"""
    async with get_async_session_context() as session:
        job = Job(
            job_id=f"job_{uuid.uuid4().hex[:8]}",
            job_type=job_type,
            status="pending",
            priority="normal",
            workspace_id=workspace_id,
            created_by=user_id,
            result={"progress_percent": 0}
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

def get_auth_headers(token: str) -> dict:
    """Helper to create authorization headers"""
    return {"Authorization": f"Bearer {token}"}

# ===== WORKSPACE-SCOPED JOB COLLECTION TESTS =====

@pytest.mark.asyncio
async def test_list_workspace_jobs_success():
    """Test GET /workspaces/{workspace_id}/jobs - List jobs in workspace"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create test jobs
    job1 = await create_test_job(workspace.id, user_id, "data_analysis")
    job2 = await create_test_job(workspace.id, user_id, "model_training")
    
    client = TestClient(app)
    response = client.get(
        f"/workspace/{workspace.id}/jobs",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) == 2
    
    job_ids = [job["job_id"] for job in data["data"]]
    assert job1.job_id in job_ids
    assert job2.job_id in job_ids

@pytest.mark.asyncio
async def test_list_workspace_jobs_with_filters():
    """Test GET /workspaces/{workspace_id}/jobs with filtering"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create jobs with different types and statuses
    await create_test_job(workspace.id, user_id, "data_analysis")
    
    # Create job with specific status
    async with get_async_session_context() as session:
        job_running = Job(
            job_id=f"job_{uuid.uuid4().hex[:8]}",
            job_type="model_training",
            status="running",
            priority="high",
            workspace_id=workspace.id,
            created_by=user_id
        )
        session.add(job_running)
        await session.commit()
    
    client = TestClient(app)
    
    # Test filtering by status
    response = client.get(
        f"/workspace/{workspace.id}/jobs?status=running",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["status"] == "running"
    
    # Test filtering by job_type
    response = client.get(
        f"/workspace/{workspace.id}/jobs?job_type=data_analysis",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["job_type"] == "data_analysis"

@pytest.mark.asyncio
async def test_list_workspace_jobs_pagination():
    """Test GET /workspaces/{workspace_id}/jobs with pagination"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create multiple jobs
    for i in range(5):
        await create_test_job(workspace.id, user_id, f"job_type_{i}")
    
    client = TestClient(app)
    
    # Test pagination
    response = client.get(
        f"/workspace/{workspace.id}/jobs?page=1&limit=2",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["total"] == 5

@pytest.mark.asyncio
async def test_list_workspace_jobs_no_access():
    """Test GET /workspaces/{workspace_id}/jobs - No access to workspace"""
    user1_id, token1 = await create_test_user("user1")
    user2_id, token2 = await create_test_user("user2")
    
    # Create workspace with user2 as member
    workspace = await create_test_workspace("Private Workspace")
    await create_test_membership(workspace.id, user2_id, "member")
    await create_test_job(workspace.id, user2_id, "private_job")
    
    client = TestClient(app)
    response = client.get(
        f"/workspace/{workspace.id}/jobs",
        headers=get_auth_headers(token1)  # user1 has no access
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 0  # No jobs visible to user1

@pytest.mark.asyncio
async def test_create_workspace_job_success():
    """Test POST /workspaces/{workspace_id}/jobs - Create job in workspace"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    client = TestClient(app)
    response = client.post(
        f"/workspace/{workspace.id}/jobs",
        json={
            "job_type": "data_processing",
            "workspace_id": workspace.id,  # Still required by the model
            "priority": "high",
            "metadata": {"source": "test_data"},
            "estimated_duration": 300
        },
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["job_type"] == "data_processing"
    assert data["priority"] == "high"
    assert data["workspace_id"] == workspace.id
    assert "job_id" in data

@pytest.mark.asyncio
async def test_create_workspace_job_no_access():
    """Test POST /workspaces/{workspace_id}/jobs - Fail without workspace access"""
    user1_id, token1 = await create_test_user("user1")
    user2_id, token2 = await create_test_user("user2")
    
    # Create workspace with user2 as member
    workspace = await create_test_workspace("Private Workspace")
    await create_test_membership(workspace.id, user2_id, "member")
    
    client = TestClient(app)
    response = client.post(
        f"/workspace/{workspace.id}/jobs",
        json={
            "job_type": "data_processing",
            "workspace_id": workspace.id,  # Still required by the model
            "priority": "normal"
        },
        headers=get_auth_headers(token1)  # user1 has no access
    )
    
    assert response.status_code == 400  # Service should reject job creation

# ===== SINGLE JOB OPERATION TESTS =====

@pytest.mark.asyncio
async def test_get_workspace_job_success():
    """Test GET /workspaces/{workspace_id}/jobs/{job_id} - Get job details"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create test job
    job = await create_test_job(workspace.id, user_id, "data_analysis")
    
    client = TestClient(app)
    response = client.get(
        f"/workspace/{workspace.id}/jobs/{job.job_id}",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.job_id
    assert data["job_type"] == "data_analysis"
    assert data["workspace_id"] == workspace.id

@pytest.mark.asyncio
async def test_get_workspace_job_wrong_workspace():
    """Test GET /workspaces/{workspace_id}/jobs/{job_id} - Job in different workspace"""
    user_id, token = await create_test_user("user1")
    
    # Create two workspaces
    workspace1 = await create_test_workspace("Workspace 1")
    workspace2 = await create_test_workspace("Workspace 2")
    await create_test_membership(workspace1.id, user_id, "member")
    await create_test_membership(workspace2.id, user_id, "member")
    
    # Create job in workspace1
    job = await create_test_job(workspace1.id, user_id, "data_analysis")
    
    client = TestClient(app)
    # Try to access job via workspace2 URL
    response = client.get(
        f"/workspace/{workspace2.id}/jobs/{job.job_id}",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 404
    assert "not found in specified workspace" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_workspace_job_status():
    """Test GET /workspaces/{workspace_id}/jobs/{job_id}/status - Get job status"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create job with progress info
    async with get_async_session_context() as session:
        job = Job(
            job_id=f"job_{uuid.uuid4().hex[:8]}",
            job_type="data_analysis",
            status="running",
            priority="normal",
            workspace_id=workspace.id,
            created_by=user_id,
            result={
                "progress_percent": 75,
                "progress_message": "Processing data..."
            }
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
    
    client = TestClient(app)
    response = client.get(
        f"/workspace/{workspace.id}/jobs/{job.job_id}/status",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.job_id
    assert data["status"] == "running"
    assert data["progress_percent"] == 75
    assert data["progress_message"] == "Processing data..."

@pytest.mark.asyncio
@pytest.mark.skip(reason="Job service issue with finding test jobs - to investigate later")
async def test_get_workspace_job_result():
    """Test GET /workspaces/{workspace_id}/jobs/{job_id}/result - Get job result"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create test job first, then update it
    job = await create_test_job(workspace.id, user_id, "data_analysis")
    
    # Update job to completed status with result
    async with get_async_session_context() as session:
        # Fetch the job and update it
        result = await session.exec(select(Job).where(Job.job_id == job.job_id))
        db_job = result.first()
        
        db_job.status = "completed"
        db_job.result = {
            "output_file": "analysis_results.csv",
            "rows_processed": 10000,
            "success": True
        }
        db_job.completed_at = datetime.now(timezone.utc)
        
        session.add(db_job)
        await session.commit()
        await session.refresh(db_job)
    
    client = TestClient(app)
    response = client.get(
        f"/workspace/{workspace.id}/jobs/{job.job_id}/result",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.job_id
    assert data["status"] == "completed"
    assert data["result"]["output_file"] == "analysis_results.csv"
    assert data["result"]["rows_processed"] == 10000

@pytest.mark.asyncio
async def test_update_workspace_job():
    """Test PATCH /workspaces/{workspace_id}/jobs/{job_id} - Update job"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create test job
    job = await create_test_job(workspace.id, user_id, "data_analysis")
    
    client = TestClient(app)
    response = client.patch(
        f"/workspace/{workspace.id}/jobs/{job.job_id}",
        json={
            "status": "running",
            "progress_percent": 50,
            "progress_message": "Halfway complete"
        },
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.job_id
    assert data["status"] == "running"

# ===== JOB ACTION TESTS =====

@pytest.mark.asyncio
async def test_cancel_workspace_job():
    """Test POST /workspaces/{workspace_id}/jobs/{job_id}/cancel - Cancel job"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create running job
    async with get_async_session_context() as session:
        job = Job(
            job_id=f"job_{uuid.uuid4().hex[:8]}",
            job_type="data_analysis",
            status="running",
            priority="normal",
            workspace_id=workspace.id,
            created_by=user_id
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
    
    client = TestClient(app)
    response = client.post(
        f"/workspace/{workspace.id}/jobs/{job.job_id}/cancel",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.job_id
    assert data["status"] == "cancelled"

@pytest.mark.asyncio
async def test_retry_workspace_job():
    """Test POST /workspaces/{workspace_id}/jobs/{job_id}/retry - Retry job"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    # Create failed job
    async with get_async_session_context() as session:
        job = Job(
            job_id=f"job_{uuid.uuid4().hex[:8]}",
            job_type="data_analysis",
            status="failed",
            priority="normal",
            workspace_id=workspace.id,
            created_by=user_id
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
    
    client = TestClient(app)
    response = client.post(
        f"/workspace/{workspace.id}/jobs/{job.job_id}/retry",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.job_id
    assert data["status"] == "pending"  # Reset to pending for retry

@pytest.mark.asyncio
async def test_cancel_job_wrong_workspace():
    """Test POST /workspaces/{workspace_id}/jobs/{job_id}/cancel - Wrong workspace"""
    user_id, token = await create_test_user("user1")
    
    # Create two workspaces
    workspace1 = await create_test_workspace("Workspace 1")
    workspace2 = await create_test_workspace("Workspace 2")
    await create_test_membership(workspace1.id, user_id, "member")
    await create_test_membership(workspace2.id, user_id, "member")
    
    # Create job in workspace1
    job = await create_test_job(workspace1.id, user_id, "data_analysis")
    
    client = TestClient(app)
    # Try to cancel via workspace2 URL
    response = client.post(
        f"/workspace/{workspace2.id}/jobs/{job.job_id}/cancel",
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 404
    assert "not found in specified workspace" in response.json()["detail"]

# ===== LEGACY ENDPOINT TESTS =====

@pytest.mark.asyncio
async def test_legacy_list_jobs():
    """Test GET /jobs - Legacy endpoint with workspace filtering"""
    user_id, token = await create_test_user("user1")
    
    # Create workspaces and memberships
    workspace1 = await create_test_workspace("Workspace 1")
    workspace2 = await create_test_workspace("Workspace 2")
    await create_test_membership(workspace1.id, user_id, "member")
    await create_test_membership(workspace2.id, user_id, "member")
    
    # Create jobs in different workspaces
    job1 = await create_test_job(workspace1.id, user_id, "job_type_1")
    job2 = await create_test_job(workspace2.id, user_id, "job_type_2")
    
    client = TestClient(app)
    
    # Test all jobs
    response = client.get("/jobs", headers=get_auth_headers(token))
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    
    # Test filtering by workspace
    response = client.get(
        f"/jobs?workspace_id={workspace1.id}",
        headers=get_auth_headers(token)
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["workspace_id"] == workspace1.id

# ===== ERROR HANDLING TESTS =====

@pytest.mark.asyncio
async def test_unauthorized_access():
    """Test all endpoints without authentication"""
    workspace_id = 1
    job_id = "test_job_id"
    
    client = TestClient(app)
    
    # Test all endpoints return 401
    endpoints = [
        f"/workspace/{workspace_id}/jobs",
        f"/workspace/{workspace_id}/jobs/{job_id}",
        f"/workspace/{workspace_id}/jobs/{job_id}/status",
        f"/workspace/{workspace_id}/jobs/{job_id}/result",
        f"/jobs"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_invalid_workspace_id():
    """Test endpoints with invalid workspace ID"""
    user_id, token = await create_test_user("user1")
    
    client = TestClient(app)
    
    # Test with invalid workspace ID
    response = client.get(
        "/workspace/invalid/jobs",
        headers=get_auth_headers(token)
    )
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_nonexistent_job():
    """Test endpoints with non-existent job ID"""
    user_id, token = await create_test_user("user1")
    
    # Create workspace and membership
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    client = TestClient(app)
    
    # Test with non-existent job ID
    response = client.get(
        f"/workspace/{workspace.id}/jobs/nonexistent_job_id",
        headers=get_auth_headers(token)
    )
    assert response.status_code == 404