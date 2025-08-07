# main.py
# Standard library imports
import os
import uuid
# os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"

# Third-party imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

# Local imports
from api import auth, workspace, data, job, portfolio, strategy, backtesting
from core.init import run_all
from core.logger import request_id_ctx_var
from core.settings import settings

# export environment variables
UVICORN_MODE = settings.UVICORN_MODE
FRONTEND_BUILD_DIR = settings.FRONTEND_BUILD_DIR
FRONTEND_ORIGIN = settings.FRONTEND_ORIGIN

run_all()

app = FastAPI()

# Mount routers first
app.include_router(auth.router, prefix="/auth", tags=["Authentication APIs"])
app.include_router(workspace.router, prefix="/workspace", tags=["Workspace APIs"])
app.include_router(job.router, tags=["Job APIs"])  # No prefix - includes workspace-scoped routes
app.include_router(data.router, tags=["Data Infrastructure APIs"])  # No prefix - infrastructure level
app.include_router(portfolio.router, tags=["Portfolio APIs"])  # No prefix - workspace-scoped routes
app.include_router(strategy.router, tags=["Strategy APIs"])  # No prefix - workspace-scoped routes
app.include_router(backtesting.router, tags=["Backtesting APIs"])  # No prefix - workspace-scoped routes

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_ctx_var.set(request_id)
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Check environment mode
if UVICORN_MODE == "production":
    # Serve static frontend files in production
    app.mount("/static", StaticFiles(directory=FRONTEND_BUILD_DIR + "/static"), name="static")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        return FileResponse(FRONTEND_BUILD_DIR + "/index.html")
else:
    # Enable CORS in development mode
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"], 
        allow_headers=["*"],
    )
