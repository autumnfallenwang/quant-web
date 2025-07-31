# tests/api/test_workspace_api.py
"""
Comprehensive API tests for workspace endpoints.
Tests the full API layer including request/response handling, authentication, and error cases.
"""
import pytest
import pytest_asyncio
import uuid
from fastapi.testclient import TestClient
from sqlmodel import select

from main import app
from core.init import run_all
from core.db import get_async_session_context
from core.security import create_access_token
from models.db_models import IdentityUser, UserProfile, Workspace, WorkspaceMembership

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

def get_auth_headers(token: str) -> dict:
    """Helper to create authorization headers"""
    return {"Authorization": f"Bearer {token}"}

# ===== WORKSPACE COLLECTION TESTS =====

@pytest.mark.asyncio
async def test_list_user_workspaces_success():
    """Test GET /workspaces - List user's workspaces"""
    user_id, token = await create_test_user("user1")
    
    # Create test workspaces
    workspace1 = await create_test_workspace("Workspace 1")
    workspace2 = await create_test_workspace("Workspace 2")
    workspace3 = await create_test_workspace("Workspace 3")
    
    # Create memberships (user is member of first two workspaces)
    await create_test_membership(workspace1.id, user_id, "admin")
    await create_test_membership(workspace2.id, user_id, "member")
    # User is not member of workspace3
    
    client = TestClient(app)
    response = client.get("/workspace", headers=get_auth_headers(token))
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    
    workspace_names = [w["name"] for w in data["data"]]
    assert "Workspace 1" in workspace_names
    assert "Workspace 2" in workspace_names
    assert "Workspace 3" not in workspace_names

@pytest.mark.asyncio
async def test_list_user_workspaces_empty():
    """Test GET /workspaces - Empty list when user has no workspaces"""
    user_id, token = await create_test_user("user1")
    
    client = TestClient(app)
    response = client.get("/workspace", headers=get_auth_headers(token))
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["data"] == []

@pytest.mark.asyncio
async def test_list_user_workspaces_unauthorized():
    """Test GET /workspaces - Unauthorized without token"""
    client = TestClient(app)
    response = client.get("/workspace")
    
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_workspace_success():
    """Test POST /workspaces - Create new workspace"""
    user_id, token = await create_test_user("user1")
    
    workspace_name = f"New Workspace {uuid.uuid4().hex[:8]}"
    
    client = TestClient(app)
    response = client.post(
        "/workspace",
        json={"workspace_name": workspace_name},
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == workspace_name
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_create_workspace_duplicate_name():
    """Test POST /workspaces - Fail with duplicate name"""
    user_id, token = await create_test_user("user1")
    
    # Create existing workspace
    await create_test_workspace("Existing Workspace")
    
    client = TestClient(app)
    response = client.post(
        "/workspace",
        json={"workspace_name": "Existing Workspace"},
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_workspace_invalid_data():
    """Test POST /workspaces - Fail with invalid data"""
    user_id, token = await create_test_user("user1")
    
    client = TestClient(app)
    response = client.post(
        "/workspace",
        json={},  # Missing workspace_name
        headers=get_auth_headers(token)
    )
    
    assert response.status_code == 422  # Validation error

# ===== SINGLE WORKSPACE TESTS =====

@pytest.mark.asyncio
async def test_get_workspace_details_success():
    """Test GET /workspaces/{workspace_id} - Get workspace details"""
    user_id, token = await create_test_user("user1")
    
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    client = TestClient(app)
    response = client.get(f"/workspace/{workspace.id}", headers=get_auth_headers(token))
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workspace.id
    assert data["name"] == "Test Workspace"

@pytest.mark.asyncio
async def test_get_workspace_details_no_access():
    """Test GET /workspaces/{workspace_id} - Fail without access"""
    user_id, token = await create_test_user("user1")
    
    workspace = await create_test_workspace("Private Workspace")
    # User is not a member
    
    client = TestClient(app)
    response = client.get(f"/workspace/{workspace.id}", headers=get_auth_headers(token))
    
    assert response.status_code == 403
    assert "does not have access" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_workspace_details_not_found():
    """Test GET /workspaces/{workspace_id} - Fail for non-existent workspace"""
    user_id, token = await create_test_user("user1")
    
    client = TestClient(app)
    response = client.get("/workspace/999", headers=get_auth_headers(token))
    
    assert response.status_code == 403  # Service returns access denied for non-existent

# ===== WORKSPACE MEMBERS TESTS =====

@pytest.mark.asyncio
async def test_list_workspace_members_success():
    """Test GET /workspaces/{workspace_id}/members - List workspace members"""
    user1_id, token1 = await create_test_user("user1")
    user2_id, token2 = await create_test_user("user2")
    
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")
    
    client = TestClient(app)
    response = client.get(f"/workspace/{workspace.id}/members", headers=get_auth_headers(token1))
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    
    user_ids = [m["user_profile_id"] for m in data["data"]]
    assert user1_id in user_ids
    assert user2_id in user_ids

@pytest.mark.asyncio
async def test_list_workspace_members_no_access():
    """Test GET /workspaces/{workspace_id}/members - Fail without access"""
    user1_id, token1 = await create_test_user("user1")
    user2_id, token2 = await create_test_user("user2")
    
    workspace = await create_test_workspace("Private Team")
    await create_test_membership(workspace.id, user2_id, "admin")
    # user1 is not a member
    
    client = TestClient(app)
    response = client.get(f"/workspace/{workspace.id}/members", headers=get_auth_headers(token1))
    
    assert response.status_code == 403
    assert "does not have access" in response.json()["detail"]

# ===== ADMIN ENDPOINTS TESTS =====

@pytest.mark.asyncio
async def test_invite_user_admin_success():
    """Test POST /workspaces/{workspace_id}/admin/invite - Invite user as admin"""
    user1_id, token1 = await create_test_user("admin_user")
    user2_id, token2 = await create_test_user("invited_user")
    
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    
    client = TestClient(app)
    response = client.post(
        f"/workspace/{workspace.id}/admin/invite",
        json={"invited_user_id": user2_id, "role": "member"},
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["user_profile_id"] == user2_id
    assert data["workspace_id"] == workspace.id
    assert data["role"] == "member"

@pytest.mark.asyncio
async def test_invite_user_not_admin():
    """Test POST /workspaces/{workspace_id}/admin/invite - Fail when not admin"""
    user1_id, token1 = await create_test_user("regular_user")
    user2_id, token2 = await create_test_user("invited_user")
    
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "member")  # Not admin
    
    client = TestClient(app)
    response = client.post(
        f"/workspace/{workspace.id}/admin/invite",
        json={"invited_user_id": user2_id, "role": "member"},
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 403
    assert "Only admins can invite" in response.json()["detail"]

@pytest.mark.asyncio
async def test_invite_user_already_member():
    """Test POST /workspaces/{workspace_id}/admin/invite - Fail when user already member"""
    user1_id, token1 = await create_test_user("admin_user")
    user2_id, token2 = await create_test_user("existing_member")
    
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")  # Already member
    
    client = TestClient(app)
    response = client.post(
        f"/workspace/{workspace.id}/admin/invite",
        json={"invited_user_id": user2_id, "role": "admin"},
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 400
    assert "already a member" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_member_role_admin_success():
    """Test PATCH /workspaces/{workspace_id}/admin/update-role - Update member role as admin"""
    user1_id, token1 = await create_test_user("admin_user")
    user2_id, token2 = await create_test_user("member_user")
    
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")
    
    client = TestClient(app)
    response = client.patch(
        f"/workspace/{workspace.id}/admin/update-role",
        json={"member_user_id": user2_id, "new_role": "admin"},
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_profile_id"] == user2_id
    assert data["role"] == "admin"

@pytest.mark.asyncio
async def test_update_member_role_not_admin():
    """Test PATCH /workspaces/{workspace_id}/admin/update-role - Fail when not admin"""
    user1_id, token1 = await create_test_user("regular_user")
    user2_id, token2 = await create_test_user("other_user")
    
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "member")  # Not admin
    await create_test_membership(workspace.id, user2_id, "member")
    
    client = TestClient(app)
    response = client.patch(
        f"/workspace/{workspace.id}/admin/update-role",
        json={"member_user_id": user2_id, "new_role": "admin"},
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 403
    assert "Only admins can update" in response.json()["detail"]

@pytest.mark.asyncio
async def test_remove_member_admin_success():
    """Test DELETE /workspaces/{workspace_id}/admin/members/{member_user_id} - Remove member as admin"""
    user1_id, token1 = await create_test_user("admin_user")
    user2_id, token2 = await create_test_user("member_user")
    
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")
    
    client = TestClient(app)
    response = client.delete(
        f"/workspace/{workspace.id}/admin/members/{user2_id}",
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == workspace.id
    assert data["removed_user_id"] == user2_id

@pytest.mark.asyncio
async def test_remove_member_not_admin():
    """Test DELETE /workspaces/{workspace_id}/admin/members/{member_user_id} - Fail when not admin"""
    user1_id, token1 = await create_test_user("regular_user")
    user2_id, token2 = await create_test_user("other_user")
    
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "member")  # Not admin
    await create_test_membership(workspace.id, user2_id, "member")
    
    client = TestClient(app)
    response = client.delete(
        f"/workspace/{workspace.id}/admin/members/{user2_id}",
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 403
    assert "Only admins can remove" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_workspace_admin_success():
    """Test DELETE /workspaces/{workspace_id}/admin/delete - Delete workspace as admin"""
    user1_id, token1 = await create_test_user("admin_user")
    user2_id, token2 = await create_test_user("member_user")
    
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")
    
    client = TestClient(app)
    response = client.delete(
        f"/workspace/{workspace.id}/admin/delete",
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == workspace.id
    assert data["deleted"] == True

@pytest.mark.asyncio
async def test_delete_workspace_not_admin():
    """Test DELETE /workspaces/{workspace_id}/admin/delete - Fail when not admin"""
    user1_id, token1 = await create_test_user("regular_user")
    
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user1_id, "member")  # Not admin
    
    client = TestClient(app)
    response = client.delete(
        f"/workspace/{workspace.id}/admin/delete",
        headers=get_auth_headers(token1)
    )
    
    assert response.status_code == 403
    assert "Only admins can delete" in response.json()["detail"]

# ===== ERROR HANDLING TESTS =====

@pytest.mark.asyncio
async def test_invalid_workspace_id():
    """Test API endpoints with invalid workspace ID"""
    user_id, token = await create_test_user("user1")
    
    client = TestClient(app)
    
    # Test various endpoints with invalid workspace ID
    response = client.get("/workspace/invalid", headers=get_auth_headers(token))
    assert response.status_code == 422  # Validation error
    
    response = client.get("/workspace/invalid/members", headers=get_auth_headers(token))
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_malformed_json():
    """Test API endpoints with malformed JSON"""
    user_id, token = await create_test_user("user1")
    
    client = TestClient(app)
    
    # Test with malformed JSON
    response = client.post(
        "/workspace",
        data="invalid json",
        headers={**get_auth_headers(token), "Content-Type": "application/json"}
    )
    assert response.status_code == 422  # JSON parsing error