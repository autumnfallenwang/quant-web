# api/workspace.py
from fastapi import APIRouter, HTTPException, Depends, Path

from core.security import get_current_user
from core.logger import get_logger
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
from models.db_models import UserProfile
from models.workspace_models import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    InviteUserRequest,
    UpdateMemberRoleRequest
)

router = APIRouter()
logger = get_logger(__name__)

# ===== WORKSPACE COLLECTION ENDPOINTS =====

@router.get("", status_code=200)
async def list_user_workspaces(
    current_user: UserProfile = Depends(get_current_user)
):
    """
    List all workspaces the current user belongs to.
    Following Pattern 2: Global Resources (user's workspaces)
    """
    try:
        workspaces = await get_user_workspaces(user_id=current_user.id)
        return {"data": [WorkspaceResponse.from_workspace(w) for w in workspaces]}
    except Exception as e:
        logger.error(f"Error listing workspaces for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workspaces")

@router.post("", status_code=201)
async def create_workspace_api(
    request: WorkspaceCreateRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new workspace and assign the current user as admin.
    Following Pattern 2: Global Resources (workspace creation)
    """
    logger.info(f"User {current_user.id} creating workspace '{request.workspace_name}'")
    try:
        workspace = await create_workspace(
            user_id=current_user.id,
            workspace_name=request.workspace_name
        )
        return WorkspaceResponse.from_workspace(workspace)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to create workspace")

# ===== SINGLE WORKSPACE ENDPOINTS =====

@router.get("/{workspace_id}", status_code=200)
async def get_workspace_details_api(
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get details for a specific workspace.
    Following Pattern 2: Global Resources (single resource)
    """
    try:
        workspace = await get_workspace_details(
            user_id=current_user.id,
            workspace_id=workspace_id
        )
        return WorkspaceResponse.from_workspace(workspace)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve workspace")

# ===== WORKSPACE MEMBERS ENDPOINTS =====

@router.get("/{workspace_id}/members", status_code=200)
async def list_workspace_members(
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    List all members of a workspace.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        members = await get_workspace_members(
            user_id=current_user.id,
            workspace_id=workspace_id
        )
        return {"data": [WorkspaceMemberResponse.from_membership(m) for m in members]}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing members for workspace {workspace_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve members")

# ===== ADMIN ENDPOINTS =====

@router.post("/{workspace_id}/admin/invite", status_code=201)
async def invite_user_admin_api(
    request: InviteUserRequest,
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Invite a user to the workspace (admin only).
    Following Pattern 4: Admin Actions
    """
    logger.info(f"Admin {current_user.id} inviting user {request.invited_user_id} to workspace {workspace_id}")
    try:
        membership = await invite_user_to_workspace(
            user_id=current_user.id,
            workspace_id=workspace_id,
            invited_user_id=request.invited_user_id,
            role=request.role
        )
        return WorkspaceMemberResponse.from_membership(membership)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "Only admins" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inviting user to workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to invite user")

@router.patch("/{workspace_id}/admin/update-role", status_code=200)
async def update_member_role_admin_api(
    request: UpdateMemberRoleRequest,
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update a workspace member's role (admin only).
    Following Pattern 4: Admin Actions
    """
    logger.info(f"Admin {current_user.id} updating role for user {request.member_user_id} in workspace {workspace_id}")
    try:
        membership = await update_workspace_member_role(
            user_id=current_user.id,
            workspace_id=workspace_id,
            member_user_id=request.member_user_id,
            new_role=request.new_role
        )
        return WorkspaceMemberResponse.from_membership(membership)
    except ValueError as e:
        if "not found" in str(e).lower() or "not a member" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "Only admins" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating member role: {e}")
        raise HTTPException(status_code=500, detail="Failed to update member role")

@router.delete("/{workspace_id}/admin/members/{member_user_id}", status_code=200)
async def remove_member_admin_api(
    workspace_id: int = Path(...),
    member_user_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Remove a workspace member (admin only).
    Following Pattern 4: Admin Actions
    Using path parameter for member_user_id to follow API design rulebook
    """
    logger.info(f"Admin {current_user.id} removing user {member_user_id} from workspace {workspace_id}")
    try:
        result = await remove_workspace_member(
            user_id=current_user.id,
            workspace_id=workspace_id,
            member_user_id=member_user_id
        )
        return result
    except ValueError as e:
        if "not found" in str(e).lower() or "not a member" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "Only admins" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing member: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove member")

@router.delete("/{workspace_id}/admin/delete", status_code=200)
async def delete_workspace_admin_api(
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete an entire workspace (admin only).
    Following Pattern 4: Admin Actions
    """
    logger.info(f"Admin {current_user.id} deleting workspace {workspace_id}")
    try:
        result = await delete_workspace(
            user_id=current_user.id,
            workspace_id=workspace_id
        )
        return result
    except ValueError as e:
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "Only admins" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete workspace")