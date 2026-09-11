from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import AsyncSessionLocal
from app.api.v1.endpoints.billing import generate_monthly_maintenance_cycles

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure continuous monthly maintenance cycles exist for all active orgs
    try:
        async with AsyncSessionLocal() as session:
            await generate_monthly_maintenance_cycles(session)
    except Exception as e:
        print(f"[Auto-Billing Startup Warning]: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Invenza General-Purpose SaaS Inventory Management Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Healthcheck
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "service": "Invenza Backend API",
        "version": "1.0.0",
        "ledger_engine": "Immutable movement stream",
        "vector_search": "pgvector / Qdrant ready",
        "cache": "Redis ready",
    }

# Mount API V1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
