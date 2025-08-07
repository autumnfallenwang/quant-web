# Backend Development Rulebook

> **A comprehensive guide for consistent, modern backend development**  
> This rulebook ensures all developers follow the same patterns, conventions, and best practices.

---

## 📁 **1. Project Structure**

### **Folder Organization**

```
backend/
├── api/              # REST API endpoints (FastAPI routers)
├── core/             # Core infrastructure & utilities  
├── models/           # Pydantic models for requests/responses + SQLModel DB models
├── services/         # Business logic layer (service functions)
├── tests/            # All test files organized by component
└── logs/            # Application logs (auto-generated)
```

### **Folder Responsibilities**

| Folder | Purpose | Contains |
|--------|---------|----------|
| `api/` | REST endpoints | FastAPI routers, HTTP handling, validation |
| `core/` | Infrastructure | Database, auth, logging, settings, utilities |
| `models/` | Data models | DB models (`db_models.py`), API models (`*_models.py`) |
| `services/` | Business logic | Domain logic, data processing, external integrations |
| `tests/` | Testing | Unit tests, integration tests, test utilities |

### **Core Folder Structure**
```
core/
├── db.py           # Database connections, sessions
├── security.py     # Authentication, authorization  
├── logger.py       # Centralized logging
├── settings.py     # Configuration management
└── [third_party]/  # Third-party integrations (each in own folder)
```

---

## 📝 **2. File Naming Conventions**

### **Consistent Naming Patterns**

- **API files**: `{resource}.py` (e.g., `job.py`, `workspace.py`)
- **Service files**: `{resource}_service.py` (e.g., `job_service.py`, `workspace_service.py`)
- **Model files**: 
  - `db_models.py` - All database models
  - `{resource}_models.py` - API request/response models
- **Test files**: `test_{component}.py` in `tests/{component}/` folder

### **Examples**
```
api/job.py                    # Job API endpoints
services/job_service.py       # Job business logic  
models/job_models.py         # Job API models
models/db_models.py          # All database models
tests/job/test_job_api.py    # Job API tests
tests/job/test_job_service.py # Job service tests
```

---

## 🗂️ **3. File Header Documentation**

### **Required File Headers**
Every backend file must start with:

```python
# api/job.py - Job API endpoints
# services/workspace_service.py - Workspace business logic  
# models/job_models.py - Job request/response models
```

**Format**: `# {relative_path} - {brief_description}`

### **Import Organization (PEP 8)**
```python
# Standard library imports
from datetime import datetime, UTC
from typing import Optional, Dict, List

# Third-party imports  
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

# Local imports
from core.db import get_session
from core.security import get_current_user
from models.db_models import Job, UserProfile
from services.job_service import create_job
```

**Order**: Standard library → Third-party → Local imports

---

## ⚙️ **4. Service Layer Architecture**

### **Modern Service Pattern**
```python
# services/job_service.py
async def create_job(
    user_id: int,                    # Direct parameters
    job_type: str,
    workspace_id: int,
    # ... other params
) -> Job:
    async with get_async_session_context() as session:  # Internal session management
        # Business logic here
        pass
```

### **API Layer Pattern**
```python
# api/job.py  
@router.post("/", response_model=JobResponse)
async def create_job_api(
    request: JobCreateRequest,
    current_user: UserProfile = Depends(get_current_user)  # Keep existing auth
):
    job = await create_job(
        user_id=current_user.id,     # Extract ID in API layer
        job_type=request.job_type,
        workspace_id=request.workspace_id
    )
    return convert_job_to_response(job)
```

### **Internal Engine Integration Pattern**
```python
# ✅ CORRECT - Use Service Layer for Internal APIs
from services.data_service import DataService

class StrategyEngine:
    def __init__(self, strategy, parameters):
        self.data_service = DataService()  # Service layer with business logic
        
    async def get_market_data(self, symbols):
        return await self.data_service.refresh_symbols(symbols)

# ❌ WRONG - Don't use Core directly for internal integrations
from core.data_engine import DataEngine  # Too low-level
```

### **Key Principles**
- **Service layer**: Framework-independent, async-first, takes primitive types
- **API layer**: Handles HTTP concerns, auth, validation, error responses
- **Internal engines**: Always integrate via Service Layer, never Core directly
- **Service layer is the internal API**: All cross-engine communication goes through services
- **Session management**: Services manage their own database sessions
- **Permission validation**: Built into service functions, not just API layer

### **Layer Responsibilities**
| Layer | Purpose | Used By |
|-------|---------|---------|
| **API Layer** | External HTTP endpoints | Frontend, external clients |
| **Service Layer** | Internal business API | Other engines, internal services |
| **Core Layer** | Low-level infrastructure | Service layer only |

---

## 🧪 **5. Testing Standards**

### **Test Organization**
```
tests/
├── job/
│   ├── test_job_api.py       # API endpoint tests
│   ├── test_job_service.py   # Service layer tests  
│   └── test_job_models.py    # Model validation tests
├── workspace/
│   ├── test_workspace_api.py
│   └── test_workspace_service.py
└── conftest.py               # Shared fixtures
```

### **Test Naming Convention**
```python
def test_create_job_success():
    """Test successful job creation"""
    pass

def test_create_job_invalid_workspace():
    """Test job creation with invalid workspace"""
    pass

async def test_async_service_function():
    """Test async service functions"""
    pass
```

### **Required Test Categories**
- **Happy path tests**: Normal successful operations
- **Error handling tests**: Invalid inputs, permission errors
- **Edge cases**: Boundary conditions, race conditions
- **Integration tests**: Full API-to-database flows

---

## 🌐 **6. API Design Standards**

### **RESTful Endpoints**
```python
# Resource operations
GET    /jobs                    # List jobs
POST   /jobs                    # Create job
GET    /jobs/{job_id}          # Get specific job  
PATCH  /jobs/{job_id}          # Update job
DELETE /jobs/{job_id}          # Delete job

# Sub-resources and actions
GET    /jobs/{job_id}/status   # Get job status
POST   /jobs/{job_id}/cancel   # Cancel job (action)
POST   /jobs/{job_id}/retry    # Retry job (action)
```

### **Collection Analytics Pattern**

**Problem**: Analytics endpoints that conflict with individual resource routes.

**❌ Incorrect (Route Conflict)**:
```python
GET /workspace/{id}/backtests/{backtest_id}  # Individual resource
GET /workspace/{id}/backtests/summary        # Conflicts with {backtest_id}
```

**✅ Correct Solution**: Use separate analytics resource type:
```python
GET /workspace/{id}/backtests/{backtest_id}  # Individual resource
GET /workspace/{id}/backtest-analytics       # Collection analytics
```

**Naming Convention**: `{singular-resource}-analytics`

**Examples**:
```python
GET /workspace/1/backtest-analytics   # Backtest collection summary
GET /workspace/1/portfolio-analytics  # Portfolio collection summary  
GET /workspace/1/strategy-analytics   # Strategy collection summary
```

**Rationale**:
- Analytics are conceptually different from individual resources
- No routing conflicts with resource IDs
- Clear semantic separation
- Extensible for different analytics types

### **Request/Response Models**
```python
# Always use Pydantic models
class JobCreateRequest(BaseModel):
    job_type: str = Field(..., description="Type of job")
    workspace_id: int = Field(..., description="Target workspace")
    
class JobResponse(BaseModel):
    job_id: str
    status: JobStatusType
    created_at: datetime
```

### **Error Handling**
```python
try:
    result = await service_function()
    return result
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except PermissionError as e:
    raise HTTPException(status_code=403, detail=str(e))  
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 📊 **7. Database & Models**

### **Database Models** (`models/db_models.py`)
```python
class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(unique=True, index=True)
    status: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### **API Models** (`models/{resource}_models.py`)
```python  
class JobCreateRequest(BaseModel):
    job_type: str
    workspace_id: int
    
class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime
```

---

## 📝 **8. Logging Standards**

### **Use Centralized Logger**
```python
from core.logger import get_logger

logger = get_logger(__name__)
```

### **Logging Levels**
```python
logger.info(f"Creating job {job_type} for user {user_id}")      # Normal operations
logger.warning(f"Job {job_id} retried {retry_count} times")     # Concerning but not errors  
logger.error(f"Failed to create job: {str(e)}")                # Errors that need attention
logger.debug(f"Job data: {job_data}")                          # Detailed debugging info
```

---

## 🔒 **9. Security & Authentication**

### **Authentication Pattern**
```python
# API endpoints always use dependency injection
current_user: UserProfile = Depends(get_current_user)

# Service functions get user_id as parameter  
async def service_function(user_id: int, ...):
    # Permission validation inside service
    await validate_workspace_access(user_id, workspace_id)
```

### **Permission Validation**
- **API Layer**: Authentication (token validation)
- **Service Layer**: Authorization (permission checks)
- **Always validate**: User has access to requested resources

---

## 🚀 **10. Async/Await Standards**

### **Modern Async Pattern**
```python
# Service functions: async
async def create_job(...) -> Job:
    async with get_async_session_context() as session:
        # async database operations
        
# API endpoints: async  
@router.post("/")
async def create_job_api(...):
    result = await create_job(...)  # await service calls
```

### **Session Management**
```python
# Services manage their own sessions
async def service_function():
    async with get_async_session_context() as session:
        # Database operations
        await session.commit()
        # Session automatically closed
```

---

## ✅ **11. Code Quality Standards**

### **Type Hints**
```python
# Always use type hints
async def create_job(
    user_id: int,
    job_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Job:
```

### **Error Handling**
```python
# Specific exception types
except ValueError as e:          # Business logic errors
except PermissionError as e:     # Authorization errors  
except Exception as e:           # Unexpected errors
```

### **Documentation**
```python
async def create_job(user_id: int, job_type: str) -> Job:
    """
    Create a new job in the specified workspace.
    
    Args:
        user_id: ID of the user creating the job
        job_type: Type of job to create
        
    Returns:
        Created Job instance
        
    Raises:
        ValueError: If workspace access is denied
    """
```

---

## 📋 **12. Development Checklist**

### **Before Committing Code**
- [ ] File has proper header comment with path and description
- [ ] Imports organized according to PEP 8
- [ ] All functions have type hints
- [ ] Service functions are async and framework-independent  
- [ ] API endpoints use proper HTTP status codes
- [ ] Error handling covers expected failure cases
- [ ] Logging statements at appropriate levels
- [ ] Tests written for new functionality
- [ ] No hardcoded values (use settings/config)

### **Code Review Checklist**
- [ ] Follows established patterns and conventions
- [ ] Proper separation of concerns (API vs Service layer)
- [ ] Security considerations addressed
- [ ] Performance implications considered
- [ ] Documentation is clear and helpful
- [ ] Tests are comprehensive and meaningful

---

## 🔄 **13. Future Considerations**

### **When to Refactor**
- Extract helper functions when seeing repeated code patterns
- Create shared validation utilities when permission checks are duplicated
- Consider service composition when services become too large
- Add caching layer when performance becomes an issue

### **Scaling Patterns**
- Keep services stateless for horizontal scaling
- Use async patterns for I/O intensive operations
- Consider event-driven architecture for complex workflows
- Plan for database connection pooling optimization

---

**This rulebook is a living document. Update it as patterns evolve and new best practices emerge.**