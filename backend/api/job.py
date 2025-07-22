# api/job.py
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from models.db_models import UserProfile
from models.job_models import JobRequest
from core.db import get_session
from core.security import get_current_user
from core.logger import get_logger
from core.job import get_job_status, get_job_result

logger = get_logger(__name__)

router = APIRouter()

@router.post("/{job_id}/get-status", status_code=200, response_model=dict)
def get_job_status_api(
    job_id: str,
    request: JobRequest,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get the status of a Job by ID.
    User must be a member of the workspace.
    """
    logger.info(f"Get status for job_id={job_id} in workspace_id={request.workspace_id} by user={current_user.username}")

    try:
        # Optional: you could validate workspace_id matches the Job’s FK if needed.
        status = get_job_status(
            session=session,
            current_user=current_user,
            job_id=job_id
        )
        logger.info(f"Status for job_id={job_id}: {status}")
        return {"job_id": job_id, "status": status}

    except ValueError as e:
        logger.warning(f"Job not found or unauthorized for job_id={job_id}")
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{job_id}/get-result", status_code=200, response_model=dict)
def get_job_result_api(
    job_id: str,
    request: JobRequest,
    session: Session = Depends(get_session),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get the result of a Job by ID.
    User must be a member of the workspace.
    """
    logger.info(f"Get result for job_id={job_id} in workspace_id={request.workspace_id} by user={current_user.username}")

    try:
        result = get_job_result(
            session=session,
            current_user=current_user,
            job_id=job_id
        )
        logger.info(f"Result for job_id={job_id}: {result}")
        return {"job_id": job_id, "result": result}

    except ValueError as e:
        logger.warning(f"Job not found or unauthorized for job_id={job_id}")
        raise HTTPException(status_code=404, detail=str(e))