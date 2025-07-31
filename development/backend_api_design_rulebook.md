# Modern API Design Rulebook

> **Consistent, Production-Ready REST API Design**  
> Every endpoint follows the same pattern. No exceptions. No confusion.

---

## 🎯 **Core Design Philosophy**

### **Consistency First**
- **Same pattern for all HTTP methods** - No mixing body vs query vs path parameters
- **Predictable URLs** - If you know one resource pattern, you know them all
- **Minimal cognitive load** - Developers shouldn't guess how an endpoint works

### **Resource Hierarchy Rules**
1. **Workspace-scoped resources** → Always use nested URLs
2. **Global resources** → Use flat URLs  
3. **Query parameters** → Only for filtering, sorting, pagination
4. **Request bodies** → Only for data payload (create/update)

---

## 📐 **URL Structure Patterns**

### **Pattern 1: Workspace-Scoped Resources**
*Resources that always belong to a workspace*

```
GET    /workspaces/{workspace_id}/jobs                    # List jobs in workspace
POST   /workspaces/{workspace_id}/jobs                    # Create job in workspace  
GET    /workspaces/{workspace_id}/jobs/{job_id}           # Get specific job
PATCH  /workspaces/{workspace_id}/jobs/{job_id}           # Update specific job
DELETE /workspaces/{workspace_id}/jobs/{job_id}           # Delete specific job
```

**Why this pattern:**
- ✅ URL clearly shows ownership relationship
- ✅ Permission validation is obvious from URL
- ✅ Consistent across all HTTP methods
- ✅ No confusion about where workspace_id goes

### **Pattern 2: Global Resources**  
*Resources that exist independently*

```
GET    /users                    # List all users (admin only)
POST   /users                    # Create new user
GET    /users/{user_id}          # Get user profile
PATCH  /users/{user_id}          # Update user profile  
DELETE /users/{user_id}          # Delete user
```

### **Pattern 3: Resource Actions**
*Non-CRUD operations on resources*

```
POST   /workspaces/{workspace_id}/jobs/{job_id}/cancel   # Cancel job
POST   /workspaces/{workspace_id}/jobs/{job_id}/retry    # Retry job
POST   /users/{user_id}/reset-password                   # Reset user password
```

### **Pattern 4: Admin Actions**
*Administrative operations requiring elevated permissions*

```
POST   /workspaces/{workspace_id}/admin/invite           # Invite user to workspace
PATCH  /workspaces/{workspace_id}/admin/update-role     # Update member role
DELETE /workspaces/{workspace_id}/admin/remove-member   # Remove workspace member
DELETE /workspaces/{workspace_id}/admin/delete          # Delete entire workspace
POST   /users/{user_id}/admin/suspend                   # Admin suspend user
```

**Admin URL Rules:**
- **Always use `/admin/` prefix** for operations requiring elevated permissions
- **Self-documenting** - URL immediately shows admin requirement
- **Clear separation** - Easy to apply admin-specific middleware/logging
- **Consistent pattern** - All admin actions follow same structure

---

## 🔧 **HTTP Method Standards**

### **GET - Retrieve Resources**

#### **Collection (List)**
```http
GET /workspaces/{workspace_id}/jobs?status=pending&page=1&limit=20
```
- **Path**: Contains all required context (workspace_id)
- **Query**: Only for filtering, sorting, pagination
- **Body**: Never used
- **Response**: Array of resources + metadata

#### **Single Resource**
```http
GET /workspaces/{workspace_id}/jobs/{job_id}
```
- **Path**: Contains all required identifiers
- **Query**: Rarely used (maybe for field selection)
- **Body**: Never used  
- **Response**: Single resource object

### **POST - Create Resources**

#### **Create in Collection**
```http
POST /workspaces/{workspace_id}/jobs
Content-Type: application/json

{
  "job_type": "data_processing",
  "priority": "high",
  "metadata": {...}
}
```
- **Path**: Contains parent context (workspace_id)
- **Body**: Resource data to create
- **Query**: Never used for data
- **Response**: Created resource with generated ID

#### **Resource Actions**
```http
POST /workspaces/{workspace_id}/jobs/{job_id}/cancel
Content-Type: application/json

{
  "reason": "User requested cancellation"
}
```

### **PATCH - Update Resources**

```http
PATCH /workspaces/{workspace_id}/jobs/{job_id}
Content-Type: application/json

{
  "priority": "urgent",
  "metadata": {...}
}
```
- **Path**: Contains full resource identifier
- **Body**: Fields to update (partial)
- **Query**: Never used for data
- **Response**: Updated resource

### **DELETE - Remove Resources**

```http
DELETE /workspaces/{workspace_id}/jobs/{job_id}
```
- **Path**: Contains full resource identifier  
- **Body**: Usually empty (optional reason)
- **Query**: Never used
- **Response**: 204 No Content or deletion confirmation

---

## 📊 **Query Parameter Standards**

### **Allowed Query Parameters**

#### **Filtering**
```http
GET /workspaces/{workspace_id}/jobs?status=running&job_type=analysis
```

#### **Sorting**  
```http
GET /workspaces/{workspace_id}/jobs?sort=created_at&order=desc
```

#### **Pagination**
```http
GET /workspaces/{workspace_id}/jobs?page=2&limit=50
```


### **❌ NEVER Use Query Parameters For**
- Resource creation data
- Resource update data  
- Required resource identifiers
- Authentication tokens
- File uploads

---

## 🔧 **Simple API-Layer Filtering System**

### **Clean Separation of Concerns**
- **Service Layer**: Returns ALL results (unchanged)
- **API Layer**: Handles filtering, sorting, pagination on top of results
- **Reusable helpers**: Common logic in `core/plugin.py`

### **Usage Pattern (Copy-Paste for All Collection Endpoints)**
```python
# api/job.py - Standard pattern for all collection endpoints
from core.plugin import apply_filters, apply_sorting, apply_pagination, get_pagination_params, get_sorting_params

@router.get("/workspaces/{workspace_id}/jobs")
async def list_jobs(
    workspace_id: int,
    current_user: UserProfile = Depends(get_current_user),
    # Resource-specific filters (add as needed)
    status: Optional[JobStatusType] = Query(None),
    job_type: Optional[str] = Query(None),
    priority: Optional[JobPriorityType] = Query(None),
    # Standard pagination/sorting (same for all)
    pagination: dict = Depends(get_pagination_params),
    sorting: dict = Depends(get_sorting_params)
):
    # 1. Get ALL results from service (service unchanged)
    all_jobs = await get_user_jobs(user_id=current_user.id, workspace_id=workspace_id)
    
    # 2. Apply filters/sorting/pagination in API layer
    filters = {"status": status, "job_type": job_type, "priority": priority}
    filtered_jobs = apply_filters(all_jobs, filters)
    sorted_jobs = apply_sorting(filtered_jobs, sorting["sort"], sorting["order"])
    result = apply_pagination(sorted_jobs, pagination["page"], pagination["limit"])
    
    # 3. Convert to response format
    result["data"] = [convert_job_to_response(job) for job in result["data"]]
    return result
```

### **Benefits**
- ✅ **Service layer unchanged**: No need to modify existing service functions
- ✅ **Consistent**: Same pattern across all collection endpoints  
- ✅ **Simple**: Copy-paste pattern, add resource-specific filters as query params
- ✅ **Reusable**: Helpers in `core/plugin.py` work on any list

---

## 🏗️ **Resource Relationship Patterns**

### **One-to-Many: Workspace → Jobs**
```http
# List all jobs in workspace
GET /workspaces/{workspace_id}/jobs

# Create job in workspace  
POST /workspaces/{workspace_id}/jobs

# Get specific job (workspace context required)
GET /workspaces/{workspace_id}/jobs/{job_id}
```

### **One-to-Many: Workspace → Members**
```http
# List workspace members
GET /workspaces/{workspace_id}/members

# Invite user to workspace
POST /workspaces/{workspace_id}/members

# Update member role
PATCH /workspaces/{workspace_id}/members/{user_id}

# Remove member from workspace
DELETE /workspaces/{workspace_id}/members/{user_id}
```

### **Many-to-Many: User ↔ Workspaces**
```http
# Get user's workspaces (user context)
GET /users/{user_id}/workspaces

# Get workspace members (workspace context)  
GET /workspaces/{workspace_id}/members
```

---

## 🎨 **URL Naming Conventions**

### **Resource Names**
- **Use nouns, not verbs**: `/jobs` not `/get-jobs`
- **Use plural for collections**: `/jobs` not `/job`
- **Use lowercase with hyphens**: `/job-templates` not `/jobTemplates`
- **Be consistent**: If you use `/jobs`, don't also have `/job`

### **Action Names**
- **Use verbs for actions**: `/cancel`, `/retry`, `/invite`
- **Be descriptive**: `/reset-password` not `/reset`
- **Use POST for actions**: Actions are not idempotent

### **Parameter Names**
- **Use snake_case**: `job_id`, `workspace_id`, `user_id`
- **Be descriptive**: `workspace_id` not `ws_id`
- **Match your database**: Keep consistent with DB column names

---

## 📝 **Request/Response Standards**

### **Request Headers**
```http
Content-Type: application/json
Authorization: Bearer {token}
Accept: application/json
```

### **Request Body Format**
```json
{
  "job_type": "data_analysis",
  "priority": "high", 
  "metadata": {
    "source": "user_upload",
    "format": "csv"
  },
  "scheduled_at": "2024-01-15T10:00:00Z"
}
```

### **Response Formats**

#### **Single Resource**
```json
{
  "job_id": "job_123",
  "job_type": "data_analysis",
  "status": "running",
  "workspace_id": 456,
  "created_at": "2024-01-15T09:30:00Z",
  "updated_at": "2024-01-15T09:45:00Z"
}
```

#### **Collection Response**
```json
{
  "data": [
    {
      "job_id": "job_123",
      "status": "running",
      "created_at": "2024-01-15T09:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

#### **Error Response**
```json
{
  "error": {
    "code": "WORKSPACE_ACCESS_DENIED",
    "message": "User does not have access to workspace 456",
    "details": {
      "workspace_id": 456,
      "user_id": 123,
      "required_role": "member"
    }
  }
}
```

---

## 🚦 **HTTP Status Codes**

### **Success Codes**
- **200 OK** - GET, PATCH successful
- **201 Created** - POST successful (resource created)
- **204 No Content** - DELETE successful
- **202 Accepted** - Async operation started

### **Client Error Codes**  
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Missing/invalid authentication
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource doesn't exist
- **409 Conflict** - Resource already exists or conflict
- **422 Unprocessable Entity** - Valid JSON but invalid data

### **Server Error Codes**
- **500 Internal Server Error** - Unexpected server error
- **502 Bad Gateway** - External service error
- **503 Service Unavailable** - Temporary service issue

---

## 🔐 **Security & Permission Patterns**

### **URL-Based Permission Validation**
```python
# Permission check is obvious from URL structure
@router.get("/workspaces/{workspace_id}/jobs/{job_id}")
async def get_job(workspace_id: int, job_id: str, current_user: UserProfile):
    # 1. Validate user has access to workspace_id
    # 2. Validate job belongs to workspace  
    # 3. Return job data

# Admin endpoints are clearly marked
@router.post("/workspaces/{workspace_id}/admin/invite")
async def invite_user_admin_api(workspace_id: int, current_user: UserProfile):
    # URL clearly indicates admin permission required
    # Service layer validates admin role
```

### **Consistent Permission Model**
- **Regular resources**: Check workspace membership or user ownership
- **Admin resources (`/admin/` prefix)**: Check admin role in workspace/system
- **Public resources**: Check authentication only

### **Admin Endpoint Security**
- **Always use `/admin/` URL prefix** - Makes permission requirements obvious
- **Validate in service layer** - Business logic enforces admin requirement
- **Log admin actions** - Track privileged operations for audit trails
- **Rate limit separately** - Apply stricter limits to admin endpoints

---

## 📋 **API Design Checklist**

### **For Every New Endpoint**
- [ ] URL follows established pattern (workspace-scoped vs global)
- [ ] HTTP method matches operation type (GET/POST/PATCH/DELETE)
- [ ] Query parameters only used for filtering/pagination
- [ ] Request body only used for data payload
- [ ] Response format is consistent with other endpoints
- [ ] Error responses follow standard format
- [ ] Permission validation matches URL structure
- [ ] Documentation includes example requests/responses

### **Before API Release**  
- [ ] All endpoints follow the same URL patterns
- [ ] No mixing of query vs body vs path parameters
- [ ] Response formats are consistent across endpoints
- [ ] Error handling is comprehensive
- [ ] Permission model is clear and consistent
- [ ] API documentation is complete and accurate

---

## 🌟 **Complete Example: Jobs API**

```http
# List jobs in workspace (with filtering)
GET /workspaces/123/jobs?status=running&priority=high&page=1&limit=20

# Create new job in workspace
POST /workspaces/123/jobs
{
  "job_type": "data_processing",
  "priority": "high",
  "metadata": {"source": "upload"}
}

# Get specific job
GET /workspaces/123/jobs/job_456

# Update job
PATCH /workspaces/123/jobs/job_456  
{
  "priority": "urgent",
  "metadata": {"updated_field": "value"}
}

# Cancel job (action)
POST /workspaces/123/jobs/job_456/cancel
{
  "reason": "User requested cancellation"
}

# Retry job (action)  
POST /workspaces/123/jobs/job_456/retry
{
  "reason": "Fixing previous error"
}

# Delete job
DELETE /workspaces/123/jobs/job_456
```

**Key Points:**
- ✅ Workspace ID always in URL path
- ✅ Job ID always in URL path when needed
- ✅ Query params only for filtering/pagination
- ✅ Body only for data payload
- ✅ Consistent pattern across all operations
- ✅ Clear permission boundaries

---

**This rulebook eliminates API design confusion. Every developer knows exactly where each piece of data goes.**