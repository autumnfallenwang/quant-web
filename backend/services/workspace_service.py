# services/workspace_service.py - Modern async workspace service
from typing import Dict, Any, List

from sqlmodel import select

from core.db import get_async_session_context
from core.logger import get_logger
from models.db_models import Workspace, WorkspaceMembership

logger = get_logger(__name__)

async def create_workspace(
    user_id: int,
    workspace_name: str
) -> Workspace:
    """
    Create a new workspace and assign the user as its first admin member.
    """
    logger.info(f"Creating workspace '{workspace_name}' for user_id={user_id}")

    async with get_async_session_context() as session:
        # Check if a workspace with this name already exists
        existing_result = await session.exec(
            select(Workspace).where(Workspace.name == workspace_name)
        )
        existing = existing_result.first()
        
        if existing:
            raise ValueError(f"Workspace '{workspace_name}' already exists.")

        # Create the new workspace
        workspace = Workspace(name=workspace_name)
        session.add(workspace)
        await session.flush()  # get workspace.id

        # Create WorkspaceMembership for creator
        membership = WorkspaceMembership(
            workspace_id=workspace.id,
            user_profile_id=user_id,
            role="admin"
        )
        session.add(membership)
        await session.commit()
        await session.refresh(workspace)

        logger.info(f"Workspace '{workspace_name}' created with id={workspace.id}")
        return workspace

async def get_user_workspaces(user_id: int) -> List[Workspace]:
    """
    Return all workspaces the user belongs to.
    """
    async with get_async_session_context() as session:
        result = await session.exec(
            select(Workspace)
            .join(WorkspaceMembership)
            .where(WorkspaceMembership.user_profile_id == user_id)
        )
        return result.all()

async def get_workspace_details(
    user_id: int,
    workspace_id: int
) -> Workspace:
    """
    Get details for a specific workspace, verifying the user has access.
    """
    async with get_async_session_context() as session:
        # Check workspace membership
        membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == user_id)
            )
        )
        membership = membership_result.first()

        if not membership:
            raise ValueError(f"User {user_id} does not have access to workspace {workspace_id}")

        # Get workspace details
        workspace_result = await session.exec(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = workspace_result.first()
        
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
            
        return workspace

async def get_workspace_members(
    user_id: int,
    workspace_id: int
) -> List[WorkspaceMembership]:
    """
    Get all members of a workspace (user must have access to workspace).
    """
    async with get_async_session_context() as session:
        # Verify user has access to workspace
        user_membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == user_id)
            )
        )
        if not user_membership_result.first():
            raise ValueError(f"User {user_id} does not have access to workspace {workspace_id}")

        # Get all members
        members_result = await session.exec(
            select(WorkspaceMembership)
            .where(WorkspaceMembership.workspace_id == workspace_id)
        )
        return members_result.all()

async def invite_user_to_workspace(
    user_id: int,
    workspace_id: int,
    invited_user_id: int,
    role: str
) -> WorkspaceMembership:
    """
    Invite another user to the workspace by creating a WorkspaceMembership.
    The current user must be an admin in that workspace.
    """
    async with get_async_session_context() as session:
        # Verify current user has admin role in this workspace
        admin_membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == user_id)
            )
        )
        admin_membership = admin_membership_result.first()

        if not admin_membership or admin_membership.role != "admin":
            raise ValueError("Only admins can invite users to this workspace.")

        # Check if the invited user is already a member
        existing_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == invited_user_id)
            )
        )
        if existing_result.first():
            raise ValueError("User is already a member of this workspace.")

        # Create new membership
        new_membership = WorkspaceMembership(
            workspace_id=workspace_id,
            user_profile_id=invited_user_id,
            role=role
        )
        session.add(new_membership)
        await session.commit()
        await session.refresh(new_membership)

        logger.info(f"User {invited_user_id} invited to workspace {workspace_id} with role {role}")
        return new_membership

async def update_workspace_member_role(
    user_id: int,
    workspace_id: int,
    member_user_id: int,
    new_role: str
) -> WorkspaceMembership:
    """
    Update the role of a workspace member. Only admins can do this.
    """
    async with get_async_session_context() as session:
        # Verify current user has admin role in this workspace
        admin_membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == user_id)
            )
        )
        admin_membership = admin_membership_result.first()

        if not admin_membership or admin_membership.role != "admin":
            raise ValueError("Only admins can update member roles.")

        # Find the membership to update
        target_membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == member_user_id)
            )
        )
        target_membership = target_membership_result.first()

        if not target_membership:
            raise ValueError("Target user is not a member of this workspace.")

        target_membership.role = new_role
        session.add(target_membership)
        await session.commit()
        await session.refresh(target_membership)

        logger.info(f"Updated user {member_user_id} role to {new_role} in workspace {workspace_id}")
        return target_membership

async def remove_workspace_member(
    user_id: int,
    workspace_id: int,
    member_user_id: int
) -> Dict[str, Any]:
    """
    Remove a user from the workspace. Only admins can do this.
    """
    async with get_async_session_context() as session:
        # Verify current user has admin role in this workspace
        admin_membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == user_id)
            )
        )
        admin_membership = admin_membership_result.first()

        if not admin_membership or admin_membership.role != "admin":
            raise ValueError("Only admins can remove members.")

        # Find the membership to delete
        target_membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == member_user_id)
            )
        )
        target_membership = target_membership_result.first()

        if not target_membership:
            raise ValueError("Target user is not a member of this workspace.")

        await session.delete(target_membership)
        await session.commit()

        logger.info(f"Removed user {member_user_id} from workspace {workspace_id}")
        return {
            "workspace_id": workspace_id,
            "removed_user_id": member_user_id
        }

async def delete_workspace(
    user_id: int,
    workspace_id: int
) -> Dict[str, Any]:
    """
    Delete an entire workspace. Only admins can do this.
    """
    async with get_async_session_context() as session:
        # Verify current user is an admin for this workspace
        admin_membership_result = await session.exec(
            select(WorkspaceMembership).where(
                (WorkspaceMembership.workspace_id == workspace_id) &
                (WorkspaceMembership.user_profile_id == user_id)
            )
        )
        admin_membership = admin_membership_result.first()

        if not admin_membership or admin_membership.role != "admin":
            raise ValueError("Only admins can delete this workspace.")

        # Get workspace to verify it exists
        workspace_result = await session.exec(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = workspace_result.first()

        if not workspace:
            raise ValueError(f"Workspace {workspace_id} does not exist.")

        # Delete all memberships first
        memberships_result = await session.exec(
            select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace_id)
        )
        for membership in memberships_result.all():
            await session.delete(membership)

        # Delete the workspace
        await session.delete(workspace)
        await session.commit()

        logger.info(f"Deleted workspace {workspace_id}")
        return {
            "workspace_id": workspace_id,
            "deleted": True
        }