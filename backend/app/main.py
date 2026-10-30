from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, SessionLocal, engine
from .routers import auth, cases, dashboard, ingest, institutions, matching, notifications, overlaps, reports, review, audit, sources, provenance, innovations, events
from .scheduler import start_scheduler, stop_scheduler
from .schema_guard import ensure_columns
from .services.ingestion import ensure_data_sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_columns(engine)
    db = SessionLocal()
    try:
        ensure_data_sources(db)
    finally:
        db.close()
    if settings.scheduler_enabled:
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="AICTE Integrated Institution Complaint Monitoring Dashboard with provenance-aware data integration. Simulated data is always labeled.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(institutions.router, prefix="/institutions", tags=["institutions"])
app.include_router(cases.router, prefix="/cases", tags=["cases"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
app.include_router(review.router, prefix="/review-queue", tags=["resolution-review"])
app.include_router(matching.router, prefix="/matching", tags=["matching-evaluation"])
app.include_router(overlaps.router, prefix="/overlaps", tags=["overlaps"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])
app.include_router(sources.router, prefix="/sources", tags=["data-sources"])
app.include_router(provenance.router, prefix="/provenance", tags=["provenance"])
app.include_router(innovations.router, prefix="/innovations", tags=["innovations"])
app.include_router(events.router, prefix="/events", tags=["events"])


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": "2.0.0"}
