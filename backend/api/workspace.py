from fastapi import APIRouter, HTTPException, status, Depends, Path
from sqlmodel import Session

from core.db import get_session
from core.security import get_current_user
from core.logger import get_logger
from services.workspace_service import (
    create_workspace,
    get_user_workspaces,
    get_workspace_details,
    invite_user_to_workspace,
    update_workspace_member_role,
    remove_workspace_member,
    delete_workspace
)
from models.db_models import UserProfile
from models.workspace_models import (
    WorkspaceCreateRequest,
    InviteUserRequest,
    UpdateMemberRoleRequest,
    WorkspaceDetailResponse,
    RemoveMemberRequest
)

router = APIRouter()
logger = get_logger(__name__)

@router.post("", status_code=201, response_model=dict)
def create_workspace_api(
    request: WorkspaceCreateRequest,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new workspace and assign the current user as admin.
    """
    logger.info(f"User {current_user.id} creating workspace '{request.workspace_name}'")
    try:
        result = create_workspace(
            workspace_name=request.workspace_name,
            session=session,
            current_user=current_user
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# List all workspaces the current user belongs to.
@router.get("", status_code=200, response_model=list[WorkspaceDetailResponse])
def list_user_workspaces_api(
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    List all workspaces the current user belongs to.
    """
    results = get_user_workspaces(session=session, current_user=current_user)
    return results

# Get details for a specific workspace.
@router.get("/{workspace_id}", status_code=200, response_model=WorkspaceDetailResponse)
def get_workspace_details_api(
    workspace_id: int = Path(...),
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get details for a specific workspace.
    """
    result = get_workspace_details(workspace_id, session, current_user)
    return result

# Invite a user to the workspace by user ID.
@router.post("/admin/{workspace_id}/invite-member", status_code=201, response_model=dict)
def invite_user_api(
    request: InviteUserRequest,
    workspace_id: int = Path(...),
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Invite a user to the workspace by user ID.
    Input comes from JSON body using InviteUserRequest.
    """
    invited_user = session.get(UserProfile, request.invited_user_id)
    if not invited_user:
        raise HTTPException(status_code=404, detail="Invited user not found.")

    result = invite_user_to_workspace(
        workspace_id=workspace_id,
        invited_user_profile=invited_user,
        role=request.role,
        session=session,
        current_user=current_user
    )
    return result

# Update a workspace member's role.
@router.patch("/admin/{workspace_id}/update-role", status_code=200, response_model=dict)
def update_member_role_api(
    request: UpdateMemberRoleRequest,
    workspace_id: int = Path(...),
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update a workspace member's role.
    Input JSON: member_user_id + new_role.
    """
    member_user = session.get(UserProfile, request.member_user_id)
    if not member_user:
        raise HTTPException(status_code=404, detail="Member user not found.")

    result = update_workspace_member_role(
        workspace_id=workspace_id,
        member_user_profile=member_user,
        new_role=request.new_role,
        session=session,
        current_user=current_user
    )
    return result

# Remove a workspace member.
@router.delete("/admin/{workspace_id}/remove-member", status_code=200, response_model=dict)
def remove_member_api(
    request: RemoveMemberRequest,
    workspace_id: int = Path(...),
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Remove a workspace member.
    Input JSON: member_user_id in the payload.
    """
    member_user = session.get(UserProfile, request.member_user_id)
    if not member_user:
        raise HTTPException(status_code=404, detail="Member user not found.")

    result = remove_workspace_member(
        workspace_id=workspace_id,
        member_user_profile=member_user,
        session=session,
        current_user=current_user
    )
    return result

# Delete a workspace (admin only).
@router.delete("/admin/{workspace_id}", status_code=200, response_model=dict)
def delete_workspace_api(
    workspace_id: int = Path(...),
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a workspace (admin only).
    """
    result = delete_workspace(
        workspace_id=workspace_id,
        session=session,
        current_user=current_user
    )
    return result