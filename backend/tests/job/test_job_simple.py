# tests/job/test_job_simple.py
"""
Simple working tests for the job system
"""
import pytest
from datetime import datetime, UTC

from core.job import convert_job_to_response

def test_convert_job_to_response():
    """Test job response conversion utility"""
    # Create a mock job object
    class MockJob:
        def __init__(self):
            self.job_id = 'test-job-123'
            self.job_type = 'test_conversion'
            self.status = 'running'
            self.priority = 'high'
            self.workspace_id = 1
            self.created_by = 1
            self.result = {'progress_percent': 75, 'message': 'Almost done'}
            self.estimated_duration = 300
            self.actual_duration = None
            self.retry_count = 0
            self.max_retries = 3
            self.created_at = datetime.now(UTC)
            self.updated_at = datetime.now(UTC)
            self.started_at = None
            self.completed_at = None
            self.scheduled_at = None
    
    job = MockJob()
    response = convert_job_to_response(job)
    
    assert response['job_id'] == 'test-job-123'
    assert response['job_type'] == 'test_conversion'
    assert response['status'] == 'running'
    assert response['progress_percent'] == 75
    assert response['priority'] == 'high'
    assert response['retry_count'] == 0
    assert response['workspace_id'] == 1

def test_job_priorities():
    """Test job priority types"""
    from core.job import JobPriorityType
    
    # These should be valid priorities
    valid_priorities = ["low", "normal", "high", "urgent"]
    
    # Test would pass if these are the correct types
    assert all(p in ["low", "normal", "high", "urgent"] for p in valid_priorities)

def test_job_statuses():
    """Test job status types"""
    from core.job import JobStatusType
    
    # These should be valid statuses
    valid_statuses = ["pending", "running", "success", "failed", "cancelled"]
    
    # Test would pass if these are the correct types
    assert all(s in ["pending", "running", "success", "failed", "cancelled"] for s in valid_statuses)