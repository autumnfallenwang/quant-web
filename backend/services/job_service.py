# core/job.py - Modern Async Job System
from datetime import datetime, UTC
from typing import Optional, Dict, List, Literal

from sqlmodel import select
from sqlalchemy import and_, desc, func

from core.db import get_async_session_context
from core.logger import get_logger
from models.db_models import Job, WorkspaceMembership

logger = get_logger(__name__)

# Modern type definitions
JobStatusType = Literal["pending", "running", "success", "failed", "cancelled"]
JobPriorityType = Literal["low", "normal", "high", "urgent"]

async def create_job(
    user_id: int,
    job_type: str,
    workspace_id: int,
    priority: JobPriorityType = "normal",
    metadata: Optional[Dict] = None,
    estimated_duration: Optional[int] = None,
    scheduled_at: Optional[datetime] = None,
    max_retries: int = 3
) -> Job:
    """Create a new Job record in the given workspace."""
    async with get_async_session_context() as session:
        # Check workspace membership
        result = await session.exec(
            select(WorkspaceMembership).where(
                and_(
                    WorkspaceMembership.workspace_id == workspace_id,
                    WorkspaceMembership.user_profile_id == user_id
                )
            )
        )
        membership = result.first()

        if not membership:
            raise ValueError(f"User {user_id} does not have access to workspace {workspace_id}")

        # Prepare job data
        job_data = {
            "job_type": job_type,
            "status": "pending",
            "workspace_id": workspace_id,
            "created_by": user_id,
            "priority": priority,
            "estimated_duration": estimated_duration,
            "scheduled_at": scheduled_at,
            "max_retries": max_retries,
            "result": {
                "metadata": metadata or {},
                "progress_percent": 0,
                "progress_message": "Job created"
            }
        }
        
        job = Job(**job_data)
        session.add(job)
        await session.commit()
        await session.refresh(job)

        logger.info(f"Created job {job.job_id} of type '{job_type}' for user {user_id} in workspace {workspace_id}")
        return job

async def update_job_status(
    job_id: str,
    status: JobStatusType,
    result: Optional[Dict] = None,
    user_id: Optional[int] = None,
    merge_result: bool = True
) -> Job:
    """Update the status and result of an existing Job."""
    async with get_async_session_context() as session:
        # Get the Job
        result_query = await session.exec(select(Job).where(Job.job_id == job_id))
        job = result_query.first()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Optional permission check
        if user_id is not None:
            membership_result = await session.exec(
                select(WorkspaceMembership).where(
                    and_(
                        WorkspaceMembership.workspace_id == job.workspace_id,
                        WorkspaceMembership.user_profile_id == user_id
                    )
                )
            )
            membership = membership_result.first()

            if not membership:
                raise ValueError(f"User {user_id} does not have access to workspace {job.workspace_id}")

        # Update job
        job.status = status
        job.updated_at = datetime.now(UTC)
        
        # Handle result updates
        if result is not None:
            if merge_result and job.result:
                # Merge with existing result
                updated_result = job.result.copy()
                updated_result.update(result)
                job.result = updated_result
            else:
                job.result = result

        session.add(job)
        await session.commit()
        await session.refresh(job)

        logger.info(f"Updated job {job_id} status to '{status}'")
        return job

async def get_job_by_id(user_id: int, job_id: str) -> Job:
    """Get a job by ID with permission check."""
    async with get_async_session_context() as session:
        # Get the Job
        result = await session.exec(select(Job).where(Job.job_id == job_id))
        job = result.first()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Check workspace membership
        membership_result = await session.exec(
            select(WorkspaceMembership).where(
                and_(
                    WorkspaceMembership.workspace_id == job.workspace_id,
                    WorkspaceMembership.user_profile_id == user_id
                )
            )
        )
        membership = membership_result.first()

        if not membership:
            raise ValueError(f"User {user_id} does not have access to workspace {job.workspace_id}")

        return job

async def get_job_status(user_id: int, job_id: str) -> str:
    """Get the status of a Job by ID."""
    job = await get_job_by_id(user_id, job_id)
    return job.status

async def get_job_result(user_id: int, job_id: str) -> Optional[Dict]:
    """Get the result of a Job by ID."""
    job = await get_job_by_id(user_id, job_id)
    return job.result

async def update_job_progress(
    job_id: str,
    progress_percent: int,
    message: Optional[str] = None
) -> Job:
    """Update job progress for real-time tracking."""
    progress_data = {
        "progress_percent": max(0, min(100, progress_percent)),  # Clamp 0-100
        "last_updated": datetime.now(UTC).isoformat()
    }
    
    if message:
        progress_data["progress_message"] = message
    
    return await update_job_status(
        job_id=job_id,
        status="running",
        result=progress_data,
        merge_result=True
    )

async def cancel_job(job_id: str, user_id: int, reason: Optional[str] = None) -> Job:
    """Cancel a running or pending job."""
    job = await get_job_by_id(user_id, job_id)
    
    if job.status not in ["pending", "running"]:
        raise ValueError(f"Cannot cancel job {job_id} with status '{job.status}'")
    
    cancel_data = {
        "cancelled_at": datetime.now(UTC).isoformat(),
        "cancelled_by": user_id,
        "cancellation_reason": reason or "User requested cancellation"
    }
    
    return await update_job_status(
        job_id=job_id,
        status="cancelled",
        result=cancel_data,
        merge_result=True
    )

async def get_user_jobs(
    user_id: int,
    workspace_id: Optional[int] = None,
    status_filter: Optional[JobStatusType] = None,
    job_type_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Job]:
    """Get jobs for a user with filtering options."""
    async with get_async_session_context() as session:
        # Build query with workspace membership join
        query = (
            select(Job)
            .join(WorkspaceMembership, Job.workspace_id == WorkspaceMembership.workspace_id)
            .where(WorkspaceMembership.user_profile_id == user_id)
        )
        
        # Apply filters
        if workspace_id:
            query = query.where(Job.workspace_id == workspace_id)
        if status_filter:
            query = query.where(Job.status == status_filter)
        if job_type_filter:
            query = query.where(Job.job_type == job_type_filter)
        
        # Order by created_at desc, add limit/offset
        query = query.order_by(desc(Job.created_at)).limit(limit).offset(offset)
        
        result = await session.exec(query)
        return result.all()

async def get_job_stats(user_id: int, workspace_id: Optional[int] = None) -> Dict[str, int]:
    """Get job statistics for a user."""
    async with get_async_session_context() as session:
        base_query = (
            select(Job.status, func.count(Job.id).label('count'))
            .join(WorkspaceMembership, Job.workspace_id == WorkspaceMembership.workspace_id)
            .where(WorkspaceMembership.user_profile_id == user_id)
        )
        
        if workspace_id:
            base_query = base_query.where(Job.workspace_id == workspace_id)
        
        query = base_query.group_by(Job.status)
        
        result = await session.exec(query)
        stats = {row.status: row.count for row in result.all()}
        
        # Ensure all statuses are present
        all_stats = {status: 0 for status in ["pending", "running", "success", "failed", "cancelled"]}
        all_stats.update(stats)
        all_stats["total"] = sum(stats.values())
        
        return all_stats

async def retry_job(job_id: str, user_id: int, reason: Optional[str] = None) -> Job:
    """Retry a failed job if it hasn't exceeded max retries."""
    job = await get_job_by_id(user_id, job_id)
    
    if job.status not in ["failed", "cancelled"]:
        raise ValueError(f"Cannot retry job {job_id} with status '{job.status}'")
    
    if job.retry_count >= job.max_retries:
        raise ValueError(f"Job {job_id} has exceeded maximum retry attempts ({job.max_retries})")
    
    # Increment retry count and reset job to pending
    retry_data = {
        "retry_count": job.retry_count + 1,
        "retried_at": datetime.now(UTC).isoformat(),
        "retry_reason": reason or "User requested retry",
        "progress_percent": 0,
        "progress_message": f"Retry attempt {job.retry_count + 1}"
    }
    
    return await update_job_status(
        job_id=job_id,
        status="pending",
        result=retry_data,
        merge_result=True
    )

async def get_pending_jobs(workspace_id: Optional[int] = None, limit: int = 10) -> List[Job]:
    """Get pending jobs for processing (job queue functionality)."""
    async with get_async_session_context() as session:
        query = select(Job).where(Job.status == "pending")
        
        if workspace_id:
            query = query.where(Job.workspace_id == workspace_id)
        
        # Order by priority (urgent first) then by created_at (oldest first)
        query = query.order_by(
            Job.priority.in_(["urgent", "high", "normal", "low"]),
            Job.created_at
        ).limit(limit)
        
        result = await session.exec(query)
        return result.all()

def convert_job_to_response(job: Job) -> Dict:
    """Convert Job model to API response format"""
    progress_percent = None
    if job.result and "progress_percent" in job.result:
        progress_percent = job.result["progress_percent"]
    
    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "status": job.status,
        "priority": job.priority,
        "workspace_id": job.workspace_id,
        "created_by": job.created_by,
        "result": job.result,
        "progress_percent": progress_percent,
        "estimated_duration": job.estimated_duration,
        "actual_duration": job.actual_duration,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "scheduled_at": job.scheduled_at
    }