# services/job_service.py
import threading
from datetime import datetime, UTC
from typing import Optional, Callable, Any

from sqlmodel import Session
from sqlmodel import select

from core.db import engine
from core.logger import get_logger
from models.db_models import UserProfile, Job, WorkspaceMembership

logger = get_logger(__name__)

def create_job(
    session: Session,
    user_id: int,
    job_type: str,
    workspace_id: int
) -> Job:
    """
    Create a new Job record in the given workspace.
    The job belongs to the workspace. User must be a member of the workspace.
    """

    # Check workspace membership
    membership = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_profile_id == user_id
        )
    ).first()

    if not membership:
        raise ValueError(f"User does not have access to workspace ID '{workspace_id}'.")

    # Create the Job
    job = Job(
        job_type=job_type,
        status="pending",
        workspace_id=workspace_id
    )

    session.add(job)
    session.commit()
    session.refresh(job)

    return job

def update_job_status(
    session: Session,
    user_id: int,
    job_id: str,
    status: str,
    result: Optional[dict] = None
) -> Job:
    """
    Update the status and result of an existing Job.
    User must be a member of the workspace.
    """

    # Get the Job
    job = session.exec(
        select(Job).where(Job.job_id == job_id)
    ).first()

    if not job:
        raise ValueError(f"Job {job_id} not found.")

    # Check workspace membership
    membership = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == job.workspace_id,
            WorkspaceMembership.user_profile_id == user_id
        )
    ).first()

    if not membership:
        raise ValueError(f"User does not have access to workspace ID '{job.workspace_id}'.")

    # Update fields
    job.status = status
    if result is not None:
        job.result = result

    job.updated_at = datetime.now(UTC)

    session.add(job)
    session.commit()
    session.refresh(job)

    return job

def get_job_status(
    session: Session,
    current_user: UserProfile,
    job_id: str
) -> str:
    """
    Get the status of a Job by ID.
    User must be a member of the workspace that owns the Job.
    """

    # Get the Job
    job = session.exec(
        select(Job).where(Job.job_id == job_id)
    ).first()

    if not job:
        raise ValueError(f"Job {job_id} not found.")

    # Check workspace membership
    membership = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == job.workspace_id,
            WorkspaceMembership.user_profile_id == current_user.id
        )
    ).first()

    if not membership:
        raise ValueError(f"User does not have access to workspace ID '{job.workspace_id}'.")

    return job.status

def get_job_result(
    session: Session,
    current_user: UserProfile,
    job_id: str
) -> Optional[dict]:
    """
    Get the result of a Job by ID.
    User must be a member of the workspace that owns the Job.
    """

    # Get the Job
    job = session.exec(
        select(Job).where(Job.job_id == job_id)
    ).first()

    if not job:
        raise ValueError(f"Job {job_id} not found.")

    # Check workspace membership
    membership = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == job.workspace_id,
            WorkspaceMembership.user_profile_id == current_user.id
        )
    ).first()

    if not membership:
        raise ValueError(f"User does not have access to workspace ID '{job.workspace_id}'.")

    return job.result

# def run_job_in_background(
#     *,
#     job_type: str,
#     job_fn: Callable[[], Any],
#     session: Session,
#     user_id: int,
#     workspace_id: int
# ) -> str:
#     """
#     Create a Job and run the given job_fn in a background thread.
#     Handles job status updates and logs automatically.
#     User must be a member of the workspace.
#     Returns: job_id
#     """

#     job = create_job(
#         session=session,
#         user_id=user_id,
#         job_type=job_type,
#         workspace_id=workspace_id
#     )

#     def background_task():
#         with Session(engine) as thread_session:
#             logger.info(f"Job_id={job.job_id} job_type={job_type} started by user_id={user_id}")
#             try:
#                 update_job_status(
#                     session=thread_session,
#                     user_id=user_id,
#                     job_id=job.job_id,
#                     status="running"
#                 )

#                 result = job_fn()

#                 update_job_status(
#                     session=thread_session,
#                     user_id=user_id,
#                     job_id=job.job_id,
#                     status="success",
#                     result=result
#                 )
#                 logger.info(f"Job_id={job.job_id} job_type={job_type} finished successfully")

#             except Exception as e:
#                 logger.exception(f"Job_id={job.job_id} job_type={job_type} failed: {e}")
#                 update_job_status(
#                     session=thread_session,
#                     user_id=user_id,
#                     job_id=job.job_id,
#                     status="failed",
#                     result={"error": str(e)}
#                 )

#     thread = threading.Thread(target=background_task)
#     thread.start()

#     return job.job_id