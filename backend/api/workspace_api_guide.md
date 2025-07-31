# Workspace API Guide

> **Complete guide to using the Workspace API with practical curl examples**  
> All endpoints follow our consistent design patterns with clear authentication and permission requirements.

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

## 📁 **Workspace Collection Operations**

### **List Your Workspaces**
Get all workspaces you're a member of.

```bash
curl -X GET "http://localhost:8000/workspace" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "My Team Workspace",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    },
    {
      "id": 2,
      "name": "Personal Projects",
      "created_at": "2024-01-14T09:30:00Z",
      "updated_at": "2024-01-14T09:30:00Z"
    }
  ]
}
```

### **Create New Workspace**
Create a workspace and become its admin automatically.

```bash
curl -X POST "http://localhost:8000/workspace" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_name": "Data Science Team"
  }'
```

**Response:**
```json
{
  "id": 3,
  "name": "Data Science Team",
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

**Error Responses:**
```bash
# Duplicate name (400)
{
  "detail": "Workspace 'Data Science Team' already exists."
}

# Invalid data (422)
{
  "detail": [
    {
      "loc": ["body", "workspace_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 🏢 **Single Workspace Operations**

### **Get Workspace Details**
Retrieve information about a specific workspace you have access to.

```bash
curl -X GET "http://localhost:8000/workspace/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "id": 1,
  "name": "My Team Workspace",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

**Error Responses:**
```bash
# No access (403)
{
  "detail": "User 123 does not have access to workspace 1"
}

# Invalid workspace ID (422)
{
  "detail": [
    {
      "loc": ["path", "workspace_id"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

---

## 👥 **Workspace Members**

### **List Workspace Members**
View all members of a workspace you have access to.

```bash
curl -X GET "http://localhost:8000/workspace/1/members" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "data": [
    {
      "user_profile_id": 123,
      "workspace_id": 1,
      "role": "admin",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    },
    {
      "user_profile_id": 456,
      "workspace_id": 1,
      "role": "member",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## 🛡️ **Admin Operations**

> **Note:** All admin endpoints require `/admin/` in the URL and admin role in the workspace.

### **Invite User to Workspace**
Add a new member to your workspace (admin only).

```bash
curl -X POST "http://localhost:8000/workspace/1/admin/invite" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "invited_user_id": 789,
    "role": "member"
  }'
```

**Response:**
```json
{
  "user_profile_id": 789,
  "workspace_id": 1,
  "role": "member",
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**Valid Roles:**
- `"member"` - Regular workspace access
- `"admin"` - Full workspace management permissions

**Error Responses:**
```bash
# Not admin (403)
{
  "detail": "Only admins can invite users to this workspace."
}

# User already member (400)
{
  "detail": "User 789 is already a member of workspace 1."
}

# User not found (404)
{
  "detail": "User 999 not found."
}
```

### **Update Member Role**
Change a member's role in the workspace (admin only).

```bash
curl -X PATCH "http://localhost:8000/workspace/1/admin/update-role" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "member_user_id": 456,
    "new_role": "admin"
  }'
```

**Response:**
```json
{
  "user_profile_id": 456,
  "workspace_id": 1,
  "role": "admin",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:15:00Z"
}
```

### **Remove Member from Workspace**
Remove a user from the workspace (admin only).

```bash
curl -X DELETE "http://localhost:8000/workspace/1/admin/members/456" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "workspace_id": 1,
  "removed_user_id": 456,
  "message": "User successfully removed from workspace"
}
```

**Note:** Member user ID is specified in the URL path following RESTful conventions.

### **Delete Entire Workspace**
Permanently delete a workspace and all its data (admin only).

```bash
curl -X DELETE "http://localhost:8000/workspace/1/admin/delete" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "workspace_id": 1,
  "deleted": true,
  "message": "Workspace successfully deleted"
}
```

**⚠️ Warning:** This action is irreversible and removes all workspace data.

---

## 📋 **Quick Reference**

### **URL Patterns**
```bash
# Workspace Collection
GET    /workspace                           # List user workspaces
POST   /workspace                           # Create workspace

# Single Workspace  
GET    /workspace/{id}                      # Get workspace details
GET    /workspace/{id}/members              # List workspace members

# Admin Actions (require admin role)
POST   /workspace/{id}/admin/invite         # Invite user
PATCH  /workspace/{id}/admin/update-role    # Update member role
DELETE /workspace/{id}/admin/members/{user_id}  # Remove member  
DELETE /workspace/{id}/admin/delete         # Delete workspace
```

### **HTTP Status Codes**
```bash
200 OK              # Successful GET, PATCH, DELETE
201 Created         # Successful POST (resource created)
400 Bad Request     # Invalid request data
401 Unauthorized    # Missing or invalid token
403 Forbidden       # Insufficient permissions
404 Not Found       # Resource doesn't exist
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

### **Scenario: Setting up a new team workspace**

```bash
# 1. Create workspace
curl -X POST "http://localhost:8000/workspace" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"workspace_name": "Engineering Team"}'

# Response: {"id": 5, "name": "Engineering Team", ...}

# 2. Invite team members
curl -X POST "http://localhost:8000/workspace/5/admin/invite" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invited_user_id": 101, "role": "member"}'

curl -X POST "http://localhost:8000/workspace/5/admin/invite" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invited_user_id": 102, "role": "admin"}'

# 3. Check all members
curl -X GET "http://localhost:8000/workspace/5/members" \
  -H "Authorization: Bearer $TOKEN"
```

### **Scenario: Managing member permissions**

```bash
# 1. List current members
curl -X GET "http://localhost:8000/workspace/5/members" \
  -H "Authorization: Bearer $TOKEN"

# 2. Promote member to admin
curl -X PATCH "http://localhost:8000/workspace/5/admin/update-role" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"member_user_id": 101, "new_role": "admin"}'

# 3. Remove inactive member
curl -X DELETE "http://localhost:8000/workspace/5/admin/members/102" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🚨 **Error Handling Best Practices**

### **Check Response Status**
```bash
# Always check HTTP status code
response=$(curl -w "%{http_code}" -s -o response.json \
  -X GET "http://localhost:8000/workspace" \
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

# 403 Forbidden - Check permissions
if [ "$response" -eq 403 ]; then
  echo "Insufficient permissions for this action"
fi

# 404 Not Found - Resource doesn't exist
if [ "$response" -eq 404 ]; then
  echo "Workspace or user not found"
fi
```

---

## 📝 **API Design Patterns**

This API follows consistent patterns:

1. **URL Structure:** 
   - Collection operations: `/workspace`
   - Single resource: `/workspace/{id}`
   - Nested resources: `/workspace/{id}/members`
   - Admin actions: `/workspace/{id}/admin/{action}`

2. **HTTP Methods:**
   - `GET` - Retrieve data (no body)
   - `POST` - Create resources (JSON body)
   - `PATCH` - Update resources (JSON body)
   - `DELETE` - Remove resources (query params only)

3. **Response Format:**
   - Collections: `{"data": [...]}`
   - Single resources: `{resource_data}`
   - Errors: `{"detail": "error_message"}`

4. **Authentication:**
   - All endpoints require Bearer token
   - Admin endpoints require admin role

This consistent design makes the API predictable and easy to use across all endpoints.

---

**🎯 Ready to build amazing applications with our Workspace API!**