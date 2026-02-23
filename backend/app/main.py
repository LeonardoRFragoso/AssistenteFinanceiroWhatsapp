from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import engine, Base
from app.core.redis import init_redis, close_redis
from app.core.logging import logger
from app.routers import auth, transactions, reminders, reports, webhook, billing, admin, admin_crud, test, health
from app.utils.security_middleware import SecurityHeadersMiddleware, IPRateLimitMiddleware
from app.core.config import settings
from app.core.security_validator import validate_production_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    
    try:
        # Validate critical security configuration
        validate_production_config()
        
        # Initialize database
        logger.info("Connecting to database...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
        
        # Initialize Redis (optional)
        await init_redis()
        
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    logger.info("Shutting down application...")
    try:
        await close_redis()
        await engine.dispose()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    logger.info("Application shut down successfully")


app = FastAPI(
    title="Financial Assistant API",
    description="SaaS Financial Assistant via WhatsApp",
    version="1.0.0",
    lifespan=lifespan
)

cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
if hasattr(settings, 'FRONTEND_URL') and settings.FRONTEND_URL not in cors_origins:
    cors_origins.append(settings.FRONTEND_URL)
if hasattr(settings, 'BACKEND_URL') and settings.BACKEND_URL not in cors_origins:
    cors_origins.append(settings.BACKEND_URL)

app.add_middleware(IPRateLimitMiddleware, requests_per_minute=100)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(reminders.router)
app.include_router(reports.router)
app.include_router(webhook.router)
app.include_router(billing.router)
app.include_router(admin.router)
app.include_router(admin_crud.router)
app.include_router(test.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "message": "Financial Assistant API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
