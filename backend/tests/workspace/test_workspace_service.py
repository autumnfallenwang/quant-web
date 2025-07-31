# tests/workspace/test_workspace_service.py
"""
Comprehensive tests for workspace service functions.
Uses real database with proper cleanup.
"""
import pytest
import pytest_asyncio
import os
from sqlmodel import select

from core.init import run_all
from core.db import get_async_session_context
from services.workspace_service import (
    create_workspace,
    get_user_workspaces,
    get_workspace_details,
    get_workspace_members,
    invite_user_to_workspace,
    update_workspace_member_role,
    remove_workspace_member,
    delete_workspace
)
from models.db_models import Workspace, WorkspaceMembership

# Database Setup
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup database once for all tests"""
    run_all()  # Initialize database if needed

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
        from models.db_models import UserProfile, IdentityUser
        user_result = await session.exec(select(UserProfile))
        for profile in user_result.all():
            await session.delete(profile)
        
        identity_result = await session.exec(select(IdentityUser))
        for identity in identity_result.all():
            await session.delete(identity)
            
        await session.commit()

# Test User Helpers
import uuid

async def create_test_user(base_username: str = "testuser") -> int:
    """Helper to create a test user and return their profile ID"""
    from core.db import get_async_session_context
    from models.db_models import IdentityUser, UserProfile
    
    # Make username unique to avoid collisions
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

# Test Data Helpers
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

# ===== CREATE WORKSPACE TESTS =====

@pytest.mark.asyncio
async def test_create_workspace_success():
    """Test successful workspace creation"""
    user_id = await create_test_user("user1")
    
    workspace_name = f"New Workspace {uuid.uuid4().hex[:8]}"
    result = await create_workspace(user_id=user_id, workspace_name=workspace_name)
    
    # Assertions
    assert result.name == workspace_name
    assert result.id is not None
    
    # Verify membership was created
    async with get_async_session_context() as session:
        membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == result.id) &
                (WorkspaceMembership.user_profile_id == user_id)
            )
        )
        membership = membership_result.first()
        assert membership is not None
        assert membership.role == "admin"

@pytest.mark.asyncio
async def test_create_workspace_duplicate_name():
    """Test workspace creation fails with duplicate name"""
    user_id = await create_test_user("user1")
    
    # Create existing workspace
    await create_test_workspace("Existing Workspace")
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        await create_workspace(user_id=user_id, workspace_name="Existing Workspace")

# ===== GET USER WORKSPACES TESTS =====

@pytest.mark.asyncio
async def test_get_user_workspaces_success():
    """Test getting user workspaces successfully"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace1 = await create_test_workspace("Workspace 1")
    workspace2 = await create_test_workspace("Workspace 2")
    workspace3 = await create_test_workspace("Workspace 3")
    
    # Create memberships for user 1
    await create_test_membership(workspace1.id, user1_id, "admin")
    await create_test_membership(workspace2.id, user1_id, "member")
    # User 1 is not member of workspace3
    await create_test_membership(workspace3.id, user2_id, "member")
    
    result = await get_user_workspaces(user_id=user1_id)
    
    # Assertions
    assert len(result) == 2
    workspace_names = [w.name for w in result]
    assert "Workspace 1" in workspace_names
    assert "Workspace 2" in workspace_names
    assert "Workspace 3" not in workspace_names

@pytest.mark.asyncio
async def test_get_user_workspaces_empty():
    """Test getting user workspaces when user has none"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create workspace for another user
    workspace = await create_test_workspace("Other Workspace")
    await create_test_membership(workspace.id, user2_id, "admin")
    
    result = await get_user_workspaces(user_id=user1_id)
    
    # Assertions
    assert result == []

# ===== GET WORKSPACE DETAILS TESTS =====

@pytest.mark.asyncio
async def test_get_workspace_details_success():
    """Test getting workspace details successfully"""
    user_id = await create_test_user("user1")
    
    # Create test data
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")
    
    result = await get_workspace_details(user_id=user_id, workspace_id=workspace.id)
    
    # Assertions
    assert result.id == workspace.id
    assert result.name == "Test Workspace"

@pytest.mark.asyncio
async def test_get_workspace_details_no_access():
    """Test getting workspace details when user has no access"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create workspace for another user
    workspace = await create_test_workspace("Private Workspace")
    await create_test_membership(workspace.id, user2_id, "admin")
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="does not have access"):
        await get_workspace_details(user_id=user1_id, workspace_id=workspace.id)

@pytest.mark.asyncio
async def test_get_workspace_details_workspace_not_found():
    """Test getting workspace details when workspace doesn't exist"""
    user_id = await create_test_user("user1")
    
    # Test should raise ValueError for non-existent workspace
    with pytest.raises(ValueError, match="does not have access"):
        await get_workspace_details(user_id=user_id, workspace_id=999)

# ===== GET WORKSPACE MEMBERS TESTS =====

@pytest.mark.asyncio
async def test_get_workspace_members_success():
    """Test getting workspace members successfully"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    user3_id = await create_test_user("user3")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")
    await create_test_membership(workspace.id, user3_id, "member")
    
    result = await get_workspace_members(user_id=user1_id, workspace_id=workspace.id)
    
    # Assertions
    assert len(result) == 3
    user_ids = [m.user_profile_id for m in result]
    assert user1_id in user_ids
    assert user2_id in user_ids
    assert user3_id in user_ids

@pytest.mark.asyncio
async def test_get_workspace_members_no_access():
    """Test getting workspace members when user has no access"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    user3_id = await create_test_user("user3")
    
    # Create workspace for other users
    workspace = await create_test_workspace("Private Team")
    await create_test_membership(workspace.id, user2_id, "admin")
    await create_test_membership(workspace.id, user3_id, "member")
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="does not have access"):
        await get_workspace_members(user_id=user1_id, workspace_id=workspace.id)

# ===== INVITE USER TESTS =====

@pytest.mark.asyncio
async def test_invite_user_to_workspace_success():
    """Test successfully inviting user to workspace"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    
    result = await invite_user_to_workspace(
        user_id=user1_id, workspace_id=workspace.id, invited_user_id=user2_id, role="member"
    )
    
    # Assertions
    assert result.workspace_id == workspace.id
    assert result.user_profile_id == user2_id
    assert result.role == "member"

@pytest.mark.asyncio
async def test_invite_user_not_admin():
    """Test inviting user fails when current user is not admin"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "member")  # Not admin
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="Only admins can invite"):
        await invite_user_to_workspace(
            user_id=user1_id, workspace_id=workspace.id, invited_user_id=user2_id, role="member"
        )

@pytest.mark.asyncio
async def test_invite_user_already_member():
    """Test inviting user fails when user is already a member"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")  # Already member
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="already a member"):
        await invite_user_to_workspace(
            user_id=user1_id, workspace_id=workspace.id, invited_user_id=user2_id, role="admin"
        )

# ===== UPDATE MEMBER ROLE TESTS =====

@pytest.mark.asyncio
async def test_update_workspace_member_role_success():
    """Test successfully updating member role"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")
    
    result = await update_workspace_member_role(
        user_id=user1_id, workspace_id=workspace.id, member_user_id=user2_id, new_role="admin"
    )
    
    # Assertions
    assert result.role == "admin"
    assert result.user_profile_id == user2_id

@pytest.mark.asyncio
async def test_update_member_role_not_admin():
    """Test updating member role fails when current user is not admin"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "member")  # Not admin
    await create_test_membership(workspace.id, user2_id, "member")
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="Only admins can update"):
        await update_workspace_member_role(
            user_id=user1_id, workspace_id=workspace.id, member_user_id=user2_id, new_role="admin"
        )

@pytest.mark.asyncio
async def test_update_member_role_target_not_member():
    """Test updating role fails when target user is not a member"""
    user1_id = await create_test_user("user1")
    non_member_id = await create_test_user("nonmember")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="not a member"):
        await update_workspace_member_role(
            user_id=user1_id, workspace_id=workspace.id, member_user_id=non_member_id, new_role="admin"
        )

# ===== REMOVE MEMBER TESTS =====

@pytest.mark.asyncio
async def test_remove_workspace_member_success():
    """Test successfully removing workspace member"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")
    
    result = await remove_workspace_member(
        user_id=user1_id, workspace_id=workspace.id, member_user_id=user2_id
    )
    
    # Assertions
    assert result["workspace_id"] == workspace.id
    assert result["removed_user_id"] == user2_id
    
    # Verify membership was removed
    async with get_async_session_context() as session:
        remaining_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace.id) &
                (WorkspaceMembership.user_profile_id == user2_id)
            )
        )
        assert remaining_result.first() is None

@pytest.mark.asyncio
async def test_remove_member_not_admin():
    """Test removing member fails when current user is not admin"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace = await create_test_workspace("Team Workspace")
    await create_test_membership(workspace.id, user1_id, "member")  # Not admin
    await create_test_membership(workspace.id, user2_id, "member")
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="Only admins can remove"):
        await remove_workspace_member(
            user_id=user1_id, workspace_id=workspace.id, member_user_id=user2_id
        )

# ===== DELETE WORKSPACE TESTS =====

@pytest.mark.asyncio
async def test_delete_workspace_success():
    """Test successfully deleting workspace"""
    user1_id = await create_test_user("user1")
    user2_id = await create_test_user("user2")
    
    # Create test data
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user1_id, "admin")
    await create_test_membership(workspace.id, user2_id, "member")
    
    result = await delete_workspace(user_id=user1_id, workspace_id=workspace.id)
    
    # Assertions
    assert result["workspace_id"] == workspace.id
    assert result["deleted"] == True
    
    # Verify workspace was deleted (this will be cleaned up by fixture anyway)
    async with get_async_session_context() as session:
        workspace_result = await session.exec(
            select(Workspace).where(Workspace.id == workspace.id)
        )
        assert workspace_result.first() is None

@pytest.mark.asyncio
async def test_delete_workspace_not_admin():
    """Test deleting workspace fails when user is not admin"""
    user_id = await create_test_user("user1")
    
    # Create test data
    workspace = await create_test_workspace("Test Workspace")
    await create_test_membership(workspace.id, user_id, "member")  # Not admin
    
    # Test should raise ValueError
    with pytest.raises(ValueError, match="Only admins can delete"):
        await delete_workspace(user_id=user_id, workspace_id=workspace.id)

@pytest.mark.asyncio
async def test_delete_workspace_not_found():
    """Test deleting workspace fails when workspace doesn't exist"""
    user_id = await create_test_user("user1")
    
    # Test should raise ValueError for non-existent workspace
    with pytest.raises(ValueError, match="Only admins can delete"):
        await delete_workspace(user_id=user_id, workspace_id=999)