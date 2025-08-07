# Job API Guide

> **Complete guide to using the workspace-scoped Job API with practical curl examples**  
> Follows our modern API design patterns with consistent URL structure and filtering capabilities.

---

## 🔐 **Authentication**

All API endpoints require authentication using a Bearer token in the Authorization header.

```bash
# Get your token by logging in first
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Response will include access_token
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

**Set your token for all subsequent requests:**
```bash
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

---

## 🏢 **Workspace-Scoped Job Operations**

### **List Jobs in Workspace**
Get all jobs in a specific workspace with filtering, sorting, and pagination.

```bash
curl -X GET "http://localhost:8000/workspace/1/jobs" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "data": [
    {
      "job_id": "job_abc123",
      "job_type": "data_analysis",
      "status": "running",
      "priority": "high",
      "workspace_id": 1,
      "created_by": 123,
      "result": {
        "progress_percent": 75,
        "progress_message": "Processing data..."
      },
      "estimated_duration": 300,
      "actual_duration": null,
      "retry_count": 0,
      "max_retries": 3,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:45:00Z",
      "started_at": "2024-01-15T10:01:00Z",
      "completed_at": null,
      "scheduled_at": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1,
    "total_pages": 1
  }
}
```

### **Advanced Filtering & Pagination**
Use query parameters to filter, sort, and paginate results.

```bash
# Filter by status and job type
curl -X GET "http://localhost:8000/workspace/1/jobs?status=running&job_type=data_analysis" \
  -H "Authorization: Bearer $TOKEN"

# Filter with pagination
curl -X GET "http://localhost:8000/workspace/1/jobs?status=pending&page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Filter with sorting
curl -X GET "http://localhost:8000/workspace/1/jobs?sort=created_at&order=desc" \
  -H "Authorization: Bearer $TOKEN"

# Combined filtering, sorting, and pagination
curl -X GET "http://localhost:8000/workspace/1/jobs?priority=high&sort=updated_at&order=desc&page=1&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Available Filters:**
- `status` - Job status: `pending`, `running`, `success`, `failed`, `cancelled`
- `job_type` - Type of job: `data_analysis`, `model_training`, `data_processing`, etc.
- `priority` - Job priority: `low`, `normal`, `high`, `urgent`

**Available Sorting:**
- `sort` - Field to sort by: `created_at`, `updated_at`, `priority`, `status`
- `order` - Sort order: `asc`, `desc` (default: `desc`)

**Pagination:**
- `page` - Page number (default: 1)
- `limit` - Items per page (1-100, default: 50)

### **Create Job in Workspace**
Create a new job within a specific workspace.

```bash
curl -X POST "http://localhost:8000/workspace/1/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "data_processing",
    "workspace_id": 1,
    "priority": "high",
    "metadata": {
      "source_file": "dataset.csv",
      "output_format": "parquet",
      "filters": {"column": "value"}
    },
    "estimated_duration": 600,
    "scheduled_at": "2024-01-15T15:00:00Z"
  }'
```

**Response:**
```json
{
  "job_id": "job_def456",
  "job_type": "data_processing",
  "status": "pending",
  "priority": "high",
  "workspace_id": 1,
  "created_by": 123,
  "result": null,
  "estimated_duration": 600,
  "actual_duration": null,
  "retry_count": 0,
  "max_retries": 3,
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
  "started_at": null,
  "completed_at": null,
  "scheduled_at": "2024-01-15T15:00:00Z"
}
```

**Required Fields:**
- `job_type` - Type of job to create
- `workspace_id` - Target workspace ID (must match URL parameter)

**Optional Fields:**
- `priority` - Job priority (default: `normal`)
- `metadata` - Additional job configuration
- `estimated_duration` - Expected duration in seconds
- `scheduled_at` - Schedule job for future execution

---

## 🎯 **Single Job Operations**

### **Get Job Details**
Retrieve detailed information about a specific job.

```bash
curl -X GET "http://localhost:8000/workspace/1/jobs/job_abc123" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "job_type": "data_analysis",
  "status": "completed",
  "priority": "high",
  "workspace_id": 1,
  "created_by": 123,
  "result": {
    "output_file": "analysis_results.csv",
    "rows_processed": 50000,
    "success": true,
    "insights": ["trend_detected", "anomaly_found"]
  },
  "estimated_duration": 300,
  "actual_duration": 285,
  "retry_count": 0,
  "max_retries": 3,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:04:45Z",
  "started_at": "2024-01-15T10:01:00Z",
  "completed_at": "2024-01-15T10:04:45Z",
  "scheduled_at": null
}
```

### **Get Job Status**
Get current status and progress information for a job.

```bash
curl -X GET "http://localhost:8000/workspace/1/jobs/job_abc123/status" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "running",
  "progress_percent": 75,
  "progress_message": "Processing batch 3 of 4...",
  "updated_at": "2024-01-15T10:03:30Z"
}
```

### **Get Job Result**
Retrieve the result data from a completed job.

```bash
curl -X GET "http://localhost:8000/workspace/1/jobs/job_abc123/result" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "result": {
    "output_file": "analysis_results.csv",
    "rows_processed": 50000,
    "success": true,
    "execution_time": 285,
    "insights": ["trend_detected", "anomaly_found"],
    "metrics": {
      "accuracy": 0.95,
      "confidence": 0.87
    }
  },
  "status": "completed",
  "completed_at": "2024-01-15T10:04:45Z"
}
```

### **Update Job**
Update job status, progress, or result data.

```bash
curl -X PATCH "http://localhost:8000/workspace/1/jobs/job_abc123" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "running",
    "progress_percent": 50,
    "progress_message": "Halfway complete",
    "result": {
      "intermediate_data": "temp_results.json",
      "rows_processed": 25000
    }
  }'
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "job_type": "data_analysis",
  "status": "running",
  "priority": "high",
  "workspace_id": 1,
  "created_by": 123,
  "result": {
    "progress_percent": 50,
    "progress_message": "Halfway complete",
    "intermediate_data": "temp_results.json",
    "rows_processed": 25000
  },
  "estimated_duration": 300,
  "actual_duration": null,
  "retry_count": 0,
  "max_retries": 3,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:02:30Z",
  "started_at": "2024-01-15T10:01:00Z",
  "completed_at": null,
  "scheduled_at": null
}
```

---

## ⚡ **Job Actions**

### **Cancel Job**
Cancel a pending or running job.

```bash
curl -X POST "http://localhost:8000/workspace/1/jobs/job_abc123/cancel" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "job_type": "data_analysis",
  "status": "cancelled",
  "priority": "high",
  "workspace_id": 1,
  "created_by": 123,
  "result": {
    "cancelled_reason": "Cancelled via API",
    "partial_results": "temp_data.json"
  },
  "estimated_duration": 300,
  "actual_duration": 120,
  "retry_count": 0,
  "max_retries": 3,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:02:00Z",
  "started_at": "2024-01-15T10:01:00Z",
  "completed_at": "2024-01-15T10:02:00Z",
  "scheduled_at": null
}
```

### **Retry Job**
Retry a failed or cancelled job.

```bash
curl -X POST "http://localhost:8000/workspace/1/jobs/job_abc123/retry" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "job_type": "data_analysis",
  "status": "pending",
  "priority": "high",
  "workspace_id": 1,
  "created_by": 123,
  "result": {
    "retry_reason": "Retried via API",
    "previous_attempts": 1
  },
  "estimated_duration": 300,
  "actual_duration": null,
  "retry_count": 1,
  "max_retries": 3,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:05:00Z",
  "started_at": null,
  "completed_at": null,
  "scheduled_at": null
}
```

---

## 🔄 **Legacy Endpoints**

### **List All User Jobs (Deprecated)**
Get jobs across all workspaces for backward compatibility.

```bash
curl -X GET "http://localhost:8000/jobs" \
  -H "Authorization: Bearer $TOKEN"

# With workspace filtering
curl -X GET "http://localhost:8000/jobs?workspace_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

**⚠️ Note:** This endpoint is deprecated. Use `/workspace/{workspace_id}/jobs` instead.

---

## 📋 **Quick Reference**

### **URL Patterns**
```bash
# Workspace-Scoped Job Operations
GET    /workspace/{workspace_id}/jobs                    # List jobs in workspace
POST   /workspace/{workspace_id}/jobs                    # Create job in workspace
GET    /workspace/{workspace_id}/jobs/{job_id}           # Get job details
GET    /workspace/{workspace_id}/jobs/{job_id}/status    # Get job status
GET    /workspace/{workspace_id}/jobs/{job_id}/result    # Get job result
PATCH  /workspace/{workspace_id}/jobs/{job_id}           # Update job

# Job Actions
POST   /workspace/{workspace_id}/jobs/{job_id}/cancel    # Cancel job
POST   /workspace/{workspace_id}/jobs/{job_id}/retry     # Retry job

# Legacy (Deprecated)
GET    /jobs                                              # List all user jobs
```

### **Job Status Types**
```bash
pending     # Job queued, waiting to start
running     # Job currently executing
success     # Job completed successfully
failed      # Job failed with error
cancelled   # Job was cancelled
```

### **Job Priority Types**
```bash
low         # Low priority job
normal      # Normal priority (default)
high        # High priority job
urgent      # Urgent priority job
```

### **HTTP Status Codes**
```bash
200 OK              # Successful GET, PATCH
201 Created         # Successful POST (job created)
400 Bad Request     # Invalid request data
401 Unauthorized    # Missing or invalid token
403 Forbidden       # No access to workspace
404 Not Found       # Job or workspace not found
422 Unprocessable   # Valid JSON but invalid data
500 Internal Error  # Server error
```

### **Authentication Headers**
```bash
# Required for all endpoints
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

---

## 🔧 **Complete Examples**

### **Scenario: Data Processing Pipeline**

```bash
# 1. Create a data processing job
curl -X POST "http://localhost:8000/workspace/1/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_type": "data_processing",
    "workspace_id": 1,
    "priority": "high",
    "metadata": {
      "input_file": "raw_data.csv",
      "operations": ["clean", "transform", "aggregate"],
      "output_format": "parquet"
    },
    "estimated_duration": 1800
  }'

# Response: {"job_id": "job_xyz789", "status": "pending", ...}

# 2. Monitor job progress
curl -X GET "http://localhost:8000/workspace/1/jobs/job_xyz789/status" \
  -H "Authorization: Bearer $TOKEN"

# 3. Get final results when completed
curl -X GET "http://localhost:8000/workspace/1/jobs/job_xyz789/result" \
  -H "Authorization: Bearer $TOKEN"
```

### **Scenario: Job Management Dashboard**

```bash
# 1. Get all running jobs
curl -X GET "http://localhost:8000/workspace/1/jobs?status=running" \
  -H "Authorization: Bearer $TOKEN"

# 2. Get recent jobs (sorted by update time)
curl -X GET "http://localhost:8000/workspace/1/jobs?sort=updated_at&order=desc&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# 3. Get high priority jobs
curl -X GET "http://localhost:8000/workspace/1/jobs?priority=high&priority=urgent" \
  -H "Authorization: Bearer $TOKEN"

# 4. Cancel a problematic job
curl -X POST "http://localhost:8000/workspace/1/jobs/job_abc123/cancel" \
  -H "Authorization: Bearer $TOKEN"
```

### **Scenario: Batch Job Processing**

```bash
# 1. Create multiple jobs for batch processing
for i in {1..5}; do
  curl -X POST "http://localhost:8000/workspace/1/jobs" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"job_type\": \"batch_analysis\",
      \"workspace_id\": 1,
      \"priority\": \"normal\",
      \"metadata\": {
        \"batch_id\": $i,
        \"data_slice\": \"slice_$i.csv\"
      }
    }"
done

# 2. Monitor all batch jobs
curl -X GET "http://localhost:8000/workspace/1/jobs?job_type=batch_analysis&sort=created_at" \
  -H "Authorization: Bearer $TOKEN"

# 3. Retry any failed jobs
curl -X GET "http://localhost:8000/workspace/1/jobs?status=failed" \
  -H "Authorization: Bearer $TOKEN" | \
jq -r '.data[].job_id' | \
while read job_id; do
  curl -X POST "http://localhost:8000/workspace/1/jobs/$job_id/retry" \
    -H "Authorization: Bearer $TOKEN"
done
```

---

## 🚨 **Error Handling Best Practices**

### **Check Response Status**
```bash
# Always check HTTP status code
response=$(curl -w "%{http_code}" -s -o response.json \
  -X GET "http://localhost:8000/workspace/1/jobs" \
  -H "Authorization: Bearer $TOKEN")

if [ "$response" -eq 200 ]; then
  echo "Success"
  cat response.json
else
  echo "Error: HTTP $response"
  cat response.json
fi
```

### **Handle Common Errors**
```bash
# 401 Unauthorized - Get new token
if [ "$response" -eq 401 ]; then
  echo "Token expired, please login again"
fi

# 403 Forbidden - Check workspace access
if [ "$response" -eq 403 ]; then
  echo "No access to this workspace"
fi

# 404 Not Found - Job or workspace doesn't exist
if [ "$response" -eq 404 ]; then
  echo "Job or workspace not found"
fi

# 422 Validation Error - Check request data
if [ "$response" -eq 422 ]; then
  echo "Invalid request data, check job parameters"
  jq '.detail' response.json
fi
```

### **Workspace Security**
```bash
# Jobs are isolated by workspace
# ✅ This works - accessing job in correct workspace
curl -X GET "http://localhost:8000/workspace/1/jobs/job_abc123" \
  -H "Authorization: Bearer $TOKEN"

# ❌ This fails - trying to access job from wrong workspace
curl -X GET "http://localhost:8000/workspace/2/jobs/job_abc123" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 404 "Job not found in specified workspace"
```

---

## 📝 **API Design Patterns**

This Job API follows our consistent design patterns:

1. **URL Structure:** 
   - Workspace-scoped: `/workspace/{workspace_id}/jobs`
   - Single resource: `/workspace/{workspace_id}/jobs/{job_id}`
   - Actions: `/workspace/{workspace_id}/jobs/{job_id}/{action}`

2. **HTTP Methods:**
   - `GET` - Retrieve data (no body)
   - `POST` - Create resources or actions (JSON body)
   - `PATCH` - Update resources (JSON body)

3. **Query Parameters:**
   - Filtering: `?status=running&job_type=analysis`
   - Sorting: `?sort=created_at&order=desc`
   - Pagination: `?page=1&limit=20`

4. **Response Format:**
   - Collections: `{"data": [...], "pagination": {...}}`
   - Single resources: `{job_data}`
   - Errors: `{"detail": "error_message"}`

5. **Workspace Security:**
   - Jobs are isolated by workspace
   - URL structure enforces permission boundaries
   - Cross-workspace access is prevented

This consistent design makes the Job API predictable and easy to integrate with your applications!

---

**🚀 Ready to build powerful job processing workflows with our Job API!**