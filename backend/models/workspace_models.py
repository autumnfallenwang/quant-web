# models/workspace_models.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ===== REQUEST MODELS =====

class WorkspaceCreateRequest(BaseModel):
    workspace_name: str

class InviteUserRequest(BaseModel):
    invited_user_id: int
    role: str = "member"  # Default to member role

class UpdateMemberRoleRequest(BaseModel):
    member_user_id: int
    new_role: str

# ===== RESPONSE MODELS =====

class WorkspaceResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_workspace(cls, workspace):
        """Convert Workspace DB model to response format"""
        return cls(
            id=workspace.id,
            name=workspace.name,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at
        )

class WorkspaceMemberResponse(BaseModel):
    user_profile_id: int
    workspace_id: int
    role: str
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_membership(cls, membership):
        """Convert WorkspaceMembership DB model to response format"""
        return cls(
            user_profile_id=membership.user_profile_id,
            workspace_id=membership.workspace_id,
            role=membership.role,
            created_at=membership.created_at,
            updated_at=membership.updated_at
        )

# Legacy models for backward compatibility (if needed)
class WorkspaceDetailResponse(BaseModel):
    workspace_id: int
    workspace_name: str
    role: str
    joined_at: Optional[str] = None

class RemoveMemberRequest(BaseModel):
    member_user_id: int