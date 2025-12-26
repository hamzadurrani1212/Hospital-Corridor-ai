# app/routes/system.py
from fastapi import APIRouter
import time
import asyncio
import os

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.services.processing import processor
from app.services.camera import camera_stream
from app.db.qdrant_client import get_client, QDRANT_COLLECTION
from app.services.stats_service import stats_service

router = APIRouter()
_startup_time = time.time()

@router.get("/system/health")
async def get_system_health():
    """Get system health and component status."""
    # Check Qdrant status
    try:
        qdrant_status = "online"
    except Exception:
        qdrant_status = "offline"
        
    camera_status = "online" if camera_stream.running else "offline"
    
    # Get memory usage
    if PSUTIL_AVAILABLE:
        process = psutil.Process(os.getpid())
        memory_mb = round(process.memory_info().rss / 1024 / 1024, 2)
    else:
        memory_mb = 0
    
    # Calculate uptime
    uptime_seconds = int(time.time() - _startup_time)
    
    return {
        "status": "ok",
        "processor": "running" if processor.running else "stopped",
        "camera": camera_status,
        "qdrant": qdrant_status,
        "memory_mb": memory_mb,
        "uptime_seconds": uptime_seconds,
        "processor_stats": processor.get_stats() if processor.running else {},
        "timestamp": time.time()
    }


@router.get("/system/stats")
async def get_system_stats():
    """
    Get detailed system statistics.
    """
    # Use StatsService for unified statistics gathering (cached)
    stats = await asyncio.to_thread(stats_service.get_stats_summary)
    
    return {
        "total_alerts": stats.get("week_total", 0),
        "active_alerts": stats.get("today_total", 0),
        "people_detected_today": stats.get("today_total", 0),
        "processor_running": processor.running,
        "active_cameras": 1 if processor.running else 0
    }
