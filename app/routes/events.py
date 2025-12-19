# app/routes/events.py
from fastapi import APIRouter, UploadFile, File, Form
from app.models.clip_embedder import embedder
from app.db.qdrant_client import get_client, QDRANT_COLLECTION
from app.services.preprocessing import load_image_from_bytes
from app.services.stats_service import stats_service

router = APIRouter()


@router.post("/search/text")
async def search_text(query: str = Form(...), top_k: int = Form(5)):
    """Search for persons by text description using CLIP embeddings."""
    vec = embedder.text_embedding(query).tolist()
    
    results = get_client().query_points(
        collection_name=QDRANT_COLLECTION,
        query=vec,
        limit=top_k
    ).points
    
    return [{"id": str(h.id), "score": h.score, "payload": h.payload} for h in results]


@router.post("/search/image")
async def search_image(file: UploadFile = File(...), top_k: int = Form(5)):
    """Search for matching persons by image using CLIP embeddings."""
    data = await file.read()
    pil = load_image_from_bytes(data)
    vec = embedder.image_embedding(pil).tolist()
    
    results = get_client().query_points(
        collection_name=QDRANT_COLLECTION,
        query=vec,
        limit=top_k
    ).points
    
    return [{"id": str(h.id), "score": h.score, "payload": h.payload} for h in results]


@router.get("/events/stats")
async def get_stats():
    """Get aggregated event statistics."""
    return stats_service.get_stats_summary()

@router.get("/events/people")
async def get_people_count():
    """Get count of people detected today (Legacy endpoint for Dashboard)."""
    stats = stats_service.get_stats_summary()
    return {"count": stats.get("today_total", 0)}

@router.get("/events/recent")
async def get_recent_events(limit: int = 50):
    """Get list of recent detection events."""
    return stats_service.get_recent_events(limit)

