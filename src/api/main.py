"""Main FastAPI application."""
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.config import settings
from src.database.connection import init_db
from src.api.routes import health, jobs, admin, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📊 Database: {settings.database_url}")
    print(f"🔴 Redis: {settings.redis_url}")
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix=f"{settings.api_prefix}/health", tags=["Health"])
app.include_router(jobs.router, prefix=f"{settings.api_prefix}/jobs", tags=["Jobs"])
app.include_router(admin.router, prefix=f"{settings.api_prefix}/admin", tags=["Admin"])
app.include_router(websocket.router, tags=["WebSocket"])

# Templates
templates = Jinja2Templates(directory="templates")

# Static files (if directory exists)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass  # Static directory doesn't exist yet


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render main dashboard with real status."""
    from sqlalchemy.orm import Session
    from src.database.connection import get_db_context
    from src.database.repositories import PositionRepository
    from src.jobs.manager import job_manager
    
    # Get database stats
    with get_db_context() as db:
        repo = PositionRepository(db)
        stats = repo.get_stats()
    
    # Get RQ queue status
    try:
        queue_status = job_manager.get_all_job_statuses()
        has_running = queue_status.get("started", 0) > 0
    except Exception:
        queue_status = {"started": 0, "queued": 0, "failed": 0, "finished": 0}
        has_running = False
    
    # Build status flags
    has_running = queue_status.get("started", 0) > 0
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "stats": stats,
            "queue_status": queue_status,
            "current_status": {
                "scraper": {"running": has_running},
                "loader": {"running": has_running},
                "validator": {"running": has_running}
            },
            "sync_status": {"checked": False, "data": None},
            "error": None,
            "success_msg": None
        }
    )


@app.post("/", response_class=HTMLResponse)
async def root_post(request: Request, action: str = Form(...)):
    """Handle dashboard form actions."""
    from fastapi.responses import RedirectResponse
    from src.jobs.manager import job_manager
    
    try:
        if action == "update":
            # Trigger full pipeline
            job_manager.enqueue_pipeline()
            return RedirectResponse(url="/?msg=Pipeline+iniciado", status_code=303)
        
        else:
            return RedirectResponse(url="/?error=Ação+inválida", status_code=303)
    
    except Exception as e:
        return RedirectResponse(url=f"/?error={str(e)}", status_code=303)
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/browse", response_class=HTMLResponse)
async def browse_jobs(request: Request):
    """Render the full browse jobs page."""
    return templates.TemplateResponse(
        request=request,
        name="browse.html",
        context={}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
