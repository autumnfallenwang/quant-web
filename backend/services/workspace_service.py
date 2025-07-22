# services/workspace_service.py
from typing import Dict, Any

from sqlmodel import Session, select

from core.logger import get_logger
from models.db_models import Workspace, WorkspaceMembership, UserProfile
from models.workspace_models import WorkspaceDetailResponse

logger = get_logger(__name__)

def create_workspace(
    workspace_name: str,
    session: Session,
    current_user: UserProfile
) -> Dict[str, Any]:
    """
    Create a new workspace and assign the current user as its first admin member.
    """
    logger.info(f"Creating workspace '{workspace_name}' for user_id={current_user.id}")

    # Check if a workspace with this name already exists (optional)
    existing = session.exec(
        select(Workspace).where(Workspace.name == workspace_name)
    ).first()
    if existing:
        raise ValueError(f"Workspace '{workspace_name}' already exists.")

    # Create the new workspace
    workspace = Workspace(
        name=workspace_name)
    session.add(workspace)
    session.flush()  # get workspace.id

    # Create WorkspaceMembership for creator
    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_profile_id=current_user.id,
        role="admin"
    )
    session.add(membership)
    session.commit()

    logger.info(f"Workspace '{workspace_name}' created with id={workspace.id}")

    return {
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "membership_role": membership.role
    }

def get_user_workspaces(
    session: Session,
    current_user: UserProfile
) -> list[WorkspaceDetailResponse]:
    """
    Return all workspaces the current user belongs to,
    including the role in each.
    """
    memberships = session.exec(
        select(WorkspaceMembership)
        .where(WorkspaceMembership.user_profile_id == current_user.id)
        .join(Workspace)
    ).all()

    results = []
    for m in memberships:
        results.append(WorkspaceDetailResponse(
            workspace_id=m.workspace.id,
            workspace_name=m.workspace.name,
            role=m.role,
            joined_at=str(m.created_at) if m.created_at else None
        ))

    return results

def get_workspace_details(
    workspace_id: int,
    session: Session,
    current_user: UserProfile
) -> WorkspaceDetailResponse:
    """
    Get details for a specific workspace, verifying the user has access.
    """
    membership = session.exec(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == current_user.id
        )
        .join(Workspace)
    ).first()

    if not membership:
        raise ValueError(f"User does not have access to workspace {workspace_id}")

    workspace = membership.workspace

    return WorkspaceDetailResponse(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        role=membership.role,
        joined_at=str(membership.created_at) if membership.created_at else None
    )

def invite_user_to_workspace(
    workspace_id: int,
    invited_user_profile: UserProfile,
    role: str,
    session: Session,
    current_user: UserProfile
) -> Dict[str, Any]:
    """
    Invite another user to the workspace by creating a WorkspaceMembership.
    The current user must be an admin in that workspace.
    """
    # Verify current user has admin role in this workspace
    membership = session.exec(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == current_user.id
        )
    ).first()

    if not membership or membership.role != "admin":
        raise ValueError("Only admins can invite users to this workspace.")

    # Check if the invited user is already a member
    existing = session.exec(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == invited_user_profile.id
        )
    ).first()

    if existing:
        raise ValueError("User is already a member of this workspace.")

    # Create new membership
    new_membership = WorkspaceMembership(
        workspace_id=workspace_id,
        user_profile_id=invited_user_profile.id,
        role=role
    )
    session.add(new_membership)
    session.commit()

    return {
        "workspace_id": workspace_id,
        "invited_user_id": invited_user_profile.id,
        "role": role
    }

def update_workspace_member_role(
    workspace_id: int,
    member_user_profile: UserProfile,
    new_role: str,
    session: Session,
    current_user: UserProfile
) -> Dict[str, Any]:
    """
    Update the role of a workspace member. Only admins can do this.
    """
    # Verify current user has admin role in this workspace
    admin_membership = session.exec(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == current_user.id
        )
    ).first()

    if not admin_membership or admin_membership.role != "admin":
        raise ValueError("Only admins can update member roles.")

    # Find the membership to update
    target_membership = session.exec(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == member_user_profile.id
        )
    ).first()

    if not target_membership:
        raise ValueError("Target user is not a member of this workspace.")

    target_membership.role = new_role
    session.add(target_membership)
    session.commit()

    return {
        "workspace_id": workspace_id,
        "member_user_id": member_user_profile.id,
        "new_role": new_role
    }

def remove_workspace_member(
    workspace_id: int,
    member_user_profile: UserProfile,
    session: Session,
    current_user: UserProfile
) -> Dict[str, Any]:
    """
    Remove a user from the workspace. Only admins can do this.
    """
    # Verify current user has admin role in this workspace
    admin_membership = session.exec(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == current_user.id
        )
    ).first()

    if not admin_membership or admin_membership.role != "admin":
        raise ValueError("Only admins can remove members.")

    # Find the membership to delete
    target_membership = session.exec(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == member_user_profile.id
        )
    ).first()

    if not target_membership:
        raise ValueError("Target user is not a member of this workspace.")

    session.delete(target_membership)
    session.commit()

    return {
        "workspace_id": workspace_id,
        "removed_user_id": member_user_profile.id
    }

def delete_workspace(
    workspace_id: int,
    session: Session,
    current_user: UserProfile
) -> Dict[str, Any]:
    """
    Delete an entire workspace. Only admins can do this.
    """
    # Verify current user is an admin for this workspace
    admin_membership = session.exec(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == current_user.id
        )
    ).first()

    if not admin_membership or admin_membership.role != "admin":
        raise ValueError("Only admins can delete this workspace.")

    workspace = session.exec(
        select(Workspace).where(Workspace.id == workspace_id)
    ).first()

    if not workspace:
        raise ValueError(f"Workspace {workspace_id} does not exist.")

    for m in session.exec(
        select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace_id)
    ):
        session.delete(m)

    session.delete(workspace)
    session.commit()

    return {
        "workspace_id": workspace_id,
        "deleted": True
    }
