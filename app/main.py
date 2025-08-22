from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.middleware import LoggingMiddleware, ErrorHandlingMiddleware
from app.api.dependencies import services
from app.core.config import config
from app.core.logging import setup_logging

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="A production-ready, scalable ticketing service that allows users to hold seats temporarily and then book them.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# Include API routes
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await services.initialize()
    # Start background expiry worker
    await services.expiry_service.start_expiry_worker()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    # Stop background expiry worker
    await services.expiry_service.stop_expiry_worker()
    await services.cleanup()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Ayush_Kumar_Agrawal's Box Office API",
        "version": config.app_version,
        "docs": "/docs",
        "health": "/api/v1/health"
    }
