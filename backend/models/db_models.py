# models/db_models.py
import uuid
from datetime import datetime, UTC
from typing import Optional, List

from sqlalchemy import Column, JSON, String, Text
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint

class IdentityUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject: str
    issuer: str = "local-idp"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    user_profile: Optional["UserProfile"] = Relationship(back_populates="identity_user")

    __table_args__ = (UniqueConstraint("subject", "issuer"),)

class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="identityuser.id", unique=True)
    username: str = Field(index=True, unique=True)
    email: Optional[str] = None
    role: str = Field(default="user")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    identity_user: Optional[IdentityUser] = Relationship(back_populates="user_profile")
    workspace_memberships: List["WorkspaceMembership"] = Relationship(back_populates="user_profile")

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column("job_id", String(36), unique=True, nullable=False)
    )
    job_type: str  # e.g., 'data_refresh_all', 'data_refresh_stocks', 'custom_analysis'
    status: str = Field(default="pending")  # pending, running, success, failed, cancelled
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # Enhanced: stores progress, metadata, errors
    priority: str = Field(default="normal")  # low, normal, high, urgent
    estimated_duration: Optional[int] = Field(default=None)  # seconds
    actual_duration: Optional[int] = Field(default=None)  # seconds
    retry_count: int = Field(default=0)  # Number of retry attempts
    max_retries: int = Field(default=3)  # Maximum retry attempts
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    scheduled_at: Optional[datetime] = Field(default=None)  # For scheduled jobs

    workspace_id: int = Field(foreign_key="workspace.id")
    created_by: Optional[int] = Field(default=None, foreign_key="userprofile.id")  # Who created the job

    workspace: Optional["Workspace"] = Relationship(back_populates="jobs")

class Workspace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    memberships: List["WorkspaceMembership"] = Relationship(back_populates="workspace")
    jobs: List["Job"] = Relationship(back_populates="workspace")

class WorkspaceMembership(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    role: str = Field(default="viewer")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    workspace_id: int = Field(foreign_key="workspace.id")
    user_profile_id: int = Field(foreign_key="userprofile.id")

    workspace: Optional[Workspace] = Relationship(back_populates="memberships")
    user_profile: Optional["UserProfile"] = Relationship(back_populates="workspace_memberships")