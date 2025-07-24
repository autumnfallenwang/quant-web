# models/job_models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime

# Type definitions
JobStatusType = Literal["pending", "running", "success", "failed", "cancelled"]
JobPriorityType = Literal["low", "normal", "high", "urgent"]

class JobCreateRequest(BaseModel):
    job_type: str = Field(..., description="Type of job to create")
    workspace_id: int = Field(..., description="Target workspace ID")
    priority: JobPriorityType = Field(default="normal", description="Job priority")
    metadata: Optional[Dict] = Field(default=None, description="Additional job metadata")
    estimated_duration: Optional[int] = Field(default=None, description="Estimated duration in seconds")
    scheduled_at: Optional[datetime] = Field(default=None, description="Schedule job for later execution")

class JobRequest(BaseModel):
    workspace_id: int

class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: JobStatusType
    priority: JobPriorityType
    workspace_id: int
    created_by: Optional[int]
    result: Optional[Dict]
    progress_percent: Optional[int] = None
    estimated_duration: Optional[int]
    actual_duration: Optional[int]
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    scheduled_at: Optional[datetime]

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatusType
    progress_percent: Optional[int] = None
    progress_message: Optional[str] = None
    updated_at: datetime

class JobResultResponse(BaseModel):
    job_id: str
    result: Optional[Dict]
    status: JobStatusType
    completed_at: Optional[datetime]

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total_count: int
    page: int
    page_size: int

class JobStatsResponse(BaseModel):
    pending: int
    running: int
    success: int
    failed: int
    cancelled: int
    total: int

class JobUpdateRequest(BaseModel):
    status: Optional[JobStatusType] = None
    result: Optional[Dict] = None
    progress_percent: Optional[int] = Field(None, ge=0, le=100)
    progress_message: Optional[str] = None