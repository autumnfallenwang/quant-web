# api/job.py - Modern Job API Following Design Rulebook
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import Optional

from models.db_models import UserProfile
from models.job_models import (
    JobCreateRequest, JobStatusResponse, JobResultResponse,
    JobUpdateRequest, JobStatusType, JobPriorityType
)
from core.security import get_current_user
from core.logger import get_logger
from core.plugin import apply_filters, apply_sorting, apply_pagination, get_pagination_params, get_sorting_params
from services.job_service import (
    create_job, get_job_by_id, update_job_status, cancel_job, retry_job,
    get_user_jobs, convert_job_to_response
)

logger = get_logger(__name__)
router = APIRouter()

# ===== WORKSPACE-SCOPED JOB COLLECTION =====
# Following Pattern 1: Workspace-Scoped Resources

@router.get("/workspace/{workspace_id}/jobs")
async def list_workspace_jobs(
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user),
    # Resource-specific filters
    status: Optional[JobStatusType] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    priority: Optional[JobPriorityType] = Query(None, description="Filter by priority"),
    # Standard pagination/sorting (same for all)
    pagination: dict = Depends(get_pagination_params),
    sorting: dict = Depends(get_sorting_params)
):
    """
    List jobs in a workspace with filtering, sorting, and pagination.
    Following Pattern 1: Workspace-Scoped Resources + API-layer filtering
    """
    try:
        # 1. Get ALL results from service (service unchanged)
        all_jobs = await get_user_jobs(
            user_id=current_user.id,
            workspace_id=workspace_id
        )
        
        # 2. Apply filters/sorting/pagination in API layer
        filters = {"status": status, "job_type": job_type, "priority": priority}
        filtered_jobs = apply_filters(all_jobs, filters)
        sorted_jobs = apply_sorting(filtered_jobs, sorting["sort"], sorting["order"])
        result = apply_pagination(sorted_jobs, pagination["page"], pagination["limit"])
        
        # 3. Convert to response format
        result["data"] = [convert_job_to_response(job) for job in result["data"]]
        return result
        
    except Exception as e:
        logger.error(f"Error listing jobs for workspace {workspace_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")

@router.post("/workspace/{workspace_id}/jobs", status_code=201)
async def create_workspace_job(
    request: JobCreateRequest,
    workspace_id: int = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new job in the specified workspace.
    Following Pattern 1: Workspace-Scoped Resources
    """
    logger.info(f"Creating job type '{request.job_type}' for user {current_user.id} in workspace {workspace_id}")
    
    try:
        job = await create_job(
            user_id=current_user.id,
            job_type=request.job_type,
            workspace_id=workspace_id,
            priority=request.priority,
            metadata=request.metadata,
            estimated_duration=request.estimated_duration,
            scheduled_at=request.scheduled_at
        )
        
        response = convert_job_to_response(job)
        logger.info(f"Created job {job.job_id}")
        return response
        
    except ValueError as e:
        logger.error(f"Failed to create job: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create job")

# ===== SINGLE JOB OPERATIONS =====
# Following Pattern 1: Workspace-Scoped Resources

@router.get("/workspace/{workspace_id}/jobs/{job_id}")
async def get_workspace_job(
    workspace_id: int = Path(...),
    job_id: str = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get job details by ID within a workspace.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        job = await get_job_by_id(current_user.id, job_id)
        
        # Verify job belongs to the specified workspace
        if job.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Job not found in specified workspace")
            
        return convert_job_to_response(job)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job")

@router.get("/workspace/{workspace_id}/jobs/{job_id}/status")
async def get_workspace_job_status(
    workspace_id: int = Path(...),
    job_id: str = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get job status and progress information.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        job = await get_job_by_id(current_user.id, job_id)
        
        # Verify job belongs to the specified workspace
        if job.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Job not found in specified workspace")
        
        # Extract progress info from result
        progress_percent = None
        progress_message = None
        if job.result:
            progress_percent = job.result.get("progress_percent")
            progress_message = job.result.get("progress_message")
            
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress_percent=progress_percent,
            progress_message=progress_message,
            updated_at=job.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")

@router.get("/workspace/{workspace_id}/jobs/{job_id}/result")
async def get_workspace_job_result(
    workspace_id: int = Path(...),
    job_id: str = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get job result data.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        job = await get_job_by_id(current_user.id, job_id)
        
        # Verify job belongs to the specified workspace
        if job.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Job not found in specified workspace")
        
        return JobResultResponse(
            job_id=job.job_id,
            result=job.result,
            status=job.status,
            completed_at=job.completed_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job result {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job result")

@router.patch("/workspace/{workspace_id}/jobs/{job_id}")
async def update_workspace_job(
    request: JobUpdateRequest,
    workspace_id: int = Path(...),
    job_id: str = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update job status, result, or progress.
    Following Pattern 1: Workspace-Scoped Resources
    """
    try:
        # First verify job exists and belongs to workspace
        job = await get_job_by_id(current_user.id, job_id)
        if job.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Job not found in specified workspace")
        
        # Build result dict from request
        result_update = {}
        if request.progress_percent is not None:
            result_update["progress_percent"] = request.progress_percent
        if request.progress_message is not None:
            result_update["progress_message"] = request.progress_message
        if request.result is not None:
            result_update.update(request.result)
            
        updated_job = await update_job_status(
            job_id=job_id,
            status=request.status or "running",  # Default to running if not specified
            result=result_update if result_update else None,
            user_id=current_user.id,
            merge_result=True
        )
        
        return convert_job_to_response(updated_job)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update job")

# ===== JOB ACTIONS =====
# Following Pattern 3: Resource Actions

@router.post("/workspace/{workspace_id}/jobs/{job_id}/cancel")
async def cancel_workspace_job(
    workspace_id: int = Path(...),
    job_id: str = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Cancel a pending or running job.
    Following Pattern 3: Resource Actions
    """
    try:
        # First verify job exists and belongs to workspace
        job = await get_job_by_id(current_user.id, job_id)
        if job.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Job not found in specified workspace")
            
        cancelled_job = await cancel_job(job_id, current_user.id, "Cancelled via API")
        return convert_job_to_response(cancelled_job)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")

@router.post("/workspace/{workspace_id}/jobs/{job_id}/retry")
async def retry_workspace_job(
    workspace_id: int = Path(...),
    job_id: str = Path(...),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retry a failed or cancelled job.
    Following Pattern 3: Resource Actions
    """
    try:
        # First verify job exists and belongs to workspace
        job = await get_job_by_id(current_user.id, job_id)
        if job.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Job not found in specified workspace")
            
        retried_job = await retry_job(job_id, current_user.id, "Retried via API")
        return convert_job_to_response(retried_job)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retry job")

# ===== LEGACY GLOBAL ENDPOINTS (for backward compatibility) =====
# These may be removed in future versions

@router.get("/jobs")
async def list_all_user_jobs_legacy(
    current_user: UserProfile = Depends(get_current_user),
    workspace_id: Optional[int] = Query(None, description="Filter by workspace ID"),
    status: Optional[JobStatusType] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    pagination: dict = Depends(get_pagination_params),
    sorting: dict = Depends(get_sorting_params)
):
    """
    LEGACY: List all jobs for the current user across workspaces.
    DEPRECATED: Use /workspaces/{workspace_id}/jobs instead.
    """
    try:
        # Get ALL jobs for user (across all workspaces they have access to)
        all_jobs = await get_user_jobs(
            user_id=current_user.id,
            workspace_id=workspace_id  # None means all workspaces
        )
        
        # Apply filters/sorting/pagination in API layer
        filters = {"status": status, "job_type": job_type}
        if workspace_id:
            filters["workspace_id"] = workspace_id
            
        filtered_jobs = apply_filters(all_jobs, filters)
        sorted_jobs = apply_sorting(filtered_jobs, sorting["sort"], sorting["order"])
        result = apply_pagination(sorted_jobs, pagination["page"], pagination["limit"])
        
        # Convert to response format
        result["data"] = [convert_job_to_response(job) for job in result["data"]]
        return result
        
    except Exception as e:
        logger.error(f"Error listing jobs for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")