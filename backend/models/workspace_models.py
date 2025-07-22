from pydantic import BaseModel
from typing import Optional

class WorkspaceCreateRequest(BaseModel):
    workspace_name: str

class InviteUserRequest(BaseModel):
    invited_user_id: int
    role: str

class UpdateMemberRoleRequest(BaseModel):
    member_user_id: int
    new_role: str

class WorkspaceDetailResponse(BaseModel):
    workspace_id: int
    workspace_name: str
    role: str
    joined_at: Optional[str] = None

class RemoveMemberRequest(BaseModel):
    member_user_id: int