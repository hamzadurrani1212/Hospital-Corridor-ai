# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# -----------------------------
# ROUTES
# -----------------------------
from app.routes import embed, events, detect, stream, alerts_ws
from app.routes import staff  # ✅ NEW
from app.routes import system  # ✅ System health endpoints

# -----------------------------
# SERVICES
# -----------------------------
from app.services.processing import processor

# -----------------------------
# DB INIT
# -----------------------------
from app.db.qdrant_client import init_qdrant


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -----------------------------
    # STARTUP
    # -----------------------------
    print("🚀 Starting Hospital Corridor AI backend...")

    # Init Qdrant collections
    init_qdrant()
    print("✅ Qdrant initialized")

    # Start video processing thread
    processor.start()
    print("🎥 Video processor started")

    yield

    # -----------------------------
    # SHUTDOWN
    # -----------------------------
    print("🛑 Shutting down services...")
    processor.stop()
    print("✅ Processor stopped")


app = FastAPI(
    title="Hospital Corridor AI",
    version="1.0.0",
    lifespan=lifespan
)

# -----------------------------------
# CORS
# -----------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------
# API ROUTERS
# -----------------------------------
app.include_router(detect.router, prefix="/api", tags=["Detection"])
app.include_router(embed.router, prefix="/api", tags=["Embedding"])
app.include_router(events.router, prefix="/api", tags=["Events"])
app.include_router(stream.router, prefix="/api", tags=["Stream"])

# Alerts (REST + WebSocket)
app.include_router(alerts_ws.router)

# Authorized staff management
app.include_router(staff.router, prefix="/api", tags=["Staff"])

# System health endpoints
app.include_router(system.router, prefix="/api", tags=["System"])

# -----------------------------------
# STATIC SNAPSHOT HOSTING
# -----------------------------------
# Snapshots attached with alerts
app.mount(
    "/snapshots",
    StaticFiles(directory="snapshots"),
    name="snapshots"
)

# -----------------------------------
# ROOT HEALTH CHECK
# -----------------------------------
@app.get("/")
def read_root():
    return {
        "status": "ok",
        "service": "Hospital Corridor AI",
        "version": "1.0.0"
    }
