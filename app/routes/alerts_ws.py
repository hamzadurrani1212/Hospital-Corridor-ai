# app/routes/alerts_ws.py
"""
Alert WebSocket and REST API endpoints.
Handles alert broadcasting, storage, and management.
"""

from fastapi import APIRouter, WebSocket, Request, BackgroundTasks, HTTPException, Query
from app.broadcast import broadcaster
from app.services.alerts_store import alert_store
import base64
import uuid
import os
import asyncio
import time

router = APIRouter()

SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


# ======================================
# REST API ENDPOINTS
# ======================================

@router.post("/api/alerts")
async def receive_alert(request: Request, background: BackgroundTasks):
    """Receive an alert from external source and broadcast it."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid json: {e}")

    # Save snapshot if provided
    snapshot_url = None
    b64 = payload.get("snapshot_b64")

    if b64:
        try:
            data = base64.b64decode(b64.split(",")[-1])
            filename = f"{uuid.uuid4().hex}.jpg"
            path = os.path.join(SNAPSHOT_DIR, filename)

            with open(path, "wb") as f:
                f.write(data)

            snapshot_url = f"/snapshots/{filename}"
            payload["snapshot_url"] = snapshot_url
            payload.pop("snapshot_b64", None)

        except Exception as e:
            payload["snapshot_error"] = str(e)

    # Store alert
    stored_alert = alert_store.add_alert(payload)
    
    # Broadcast asynchronously
    background.add_task(broadcaster.broadcast_json, stored_alert)

    return {"status": "ok", "alert_id": stored_alert["id"]}


@router.get("/api/alerts")
async def get_all_alerts(limit: int = Query(100, ge=1, le=1000)):
    """Get all alerts, most recent first."""
    return alert_store.get_all(limit=limit)


@router.get("/api/alerts/recent")
async def get_recent_alerts(limit: int = Query(10, ge=1, le=50)):
    """Get most recent alerts for dashboard display."""
    alerts = alert_store.get_recent(limit=limit)
    # Format for frontend
    return [
        {
            "id": a["id"],
            "time": _format_time(a.get("timestamp", 0)),
            "camera": a.get("location", "Unknown"),
            "type": a.get("type", "UNKNOWN"),
            "status": "acknowledged" if a.get("acknowledged") else "active",
            "severity": a.get("severity", "info"),
            "title": a.get("title", "Alert"),
            "description": a.get("description", ""),
            "snapshot": a.get("snapshot")
        }
        for a in alerts
    ]


@router.get("/api/alerts/active")
async def get_active_alerts():
    """Get count of active (unacknowledged) alerts."""
    return {"count": alert_store.get_active_count()}


@router.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Mark an alert as acknowledged."""
    success = alert_store.acknowledge(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "acknowledged", "alert_id": alert_id}


@router.get("/api/alerts/{alert_id}")
async def get_alert_by_id(alert_id: str):
    """Get a specific alert by ID."""
    alert = alert_store.get_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


# ======================================
# WEBSOCKET ENDPOINT
# ======================================

@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    """WebSocket endpoint for real-time alert updates."""
    await broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                # Handle ping/pong or other client messages if needed
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping", "timestamp": time.time()})
                except Exception:
                    break
    except Exception:
        pass
    finally:
        await broadcaster.disconnect(websocket)


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    """WebSocket endpoint for real-time event updates (alias for /ws/alerts)."""
    await broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                # Handle ping/pong or other client messages if needed
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "ping", "timestamp": time.time()})
                except Exception:
                    break
    except Exception:
        pass
    finally:
        await broadcaster.disconnect(websocket)


# ======================================
# HELPER FUNCTIONS
# ======================================

def _format_time(timestamp: float) -> str:
    """Format timestamp to human readable relative time."""
    if not timestamp:
        return "Unknown"
    
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        mins = int(diff / 60)
        return f"{mins} min ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = int(diff / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
