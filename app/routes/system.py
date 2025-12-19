# app/routes/system.py
"""
System health and status endpoints.
"""

from fastapi import APIRouter
import time
import psutil
import os

router = APIRouter()

# Track startup time
_startup_time = time.time()


@router.get("/system/health")
async def get_system_health():
    """
    Get overall system health status.
    Returns processor state, camera status, memory usage, and uptime.
    """
    from app.services.processing import processor
    from app.services.camera import camera_stream
    from app.db.qdrant_client import get_client
    
    # Check Qdrant connection
    qdrant_status = "connected"
    try:
        get_client().get_collections()
    except Exception:
        qdrant_status = "error"
    
    # Check camera status
    camera_status = "online" if camera_stream.running else "offline"
    
    # Get memory usage
    process = psutil.Process(os.getpid())
    memory_mb = round(process.memory_info().rss / 1024 / 1024, 2)
    
    # Calculate uptime
    uptime_seconds = int(time.time() - _startup_time)
    
    return {
        "status": "ok",
        "processor": "running" if processor.running else "stopped",
        "camera": camera_status,
        "qdrant": qdrant_status,
        "memory_mb": memory_mb,
        "uptime_seconds": uptime_seconds,
        "timestamp": time.time()
    }


@router.get("/system/stats")
async def get_system_stats():
    """
    Get detailed system statistics.
    """
    from app.services.alerts_store import alert_store
    from app.services.processing import processor
    
    return {
        "alerts_total": len(alert_store.get_all(limit=10000)),
        "alerts_active": alert_store.get_active_count(),
        "people_detected_today": alert_store.get_people_detected_today(),
        "processor_running": processor.running,
        "timestamp": time.time()
    }
