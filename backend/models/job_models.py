# models/job_models.py
from pydantic import BaseModel

class JobRequest(BaseModel):
    workspace_id: int