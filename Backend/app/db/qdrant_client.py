import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from typing import Optional, List

# ============================
# QDRANT CONFIG
# ============================

QDRANT_COLLECTION = "authorized_staff_v3"

# client = QdrantClient(host="localhost", port=6333)
# client = QdrantClient(path="qdrant_data_v2") # Local persistence (no server required)
_client_instance = None

def get_client():
    global _client_instance
    if _client_instance is None:
        try:
            _client_instance = QdrantClient(path="qdrant_data_v2")
        except Exception as e:
            print(f"Failed to initialize Qdrant: {e}")
            raise e
    return _client_instance


# ============================
# INIT COLLECTION
# ============================

def init_qdrant():
    """
    Create Qdrant collection if it does not exist
    """
    try:
        c = get_client()
        collections = c.get_collections().collections
        if not any(c.name == QDRANT_COLLECTION for c in collections):
            c.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config={
                    "clip": VectorParams(size=512, distance=Distance.COSINE),
                    "arcface": VectorParams(size=512, distance=Distance.COSINE)
                }
            )
            print(f"[QDRANT] Collection '{QDRANT_COLLECTION}' created")
        else:
            print(f"[QDRANT] Collection '{QDRANT_COLLECTION}' already exists")
    except Exception as e:
        print(f"[QDRANT INIT ERROR] {e}")

# ============================
# INSERT AUTHORIZED STAFF
# ============================


# ============================
# INSERT AUTHORIZED STAFF
# ============================

def insert_staff_embeddings_multi(
    staff_id: str,
    embeddings: List[dict], # List of {"clip": vec, "arcface": vec, "angle": str}
    base_payload: dict
):
    """
    Insert multiple embeddings for a single staff member (different angles).
    Each angle is stored as a separate point with a comprehensive payload.
    """
    points = []
    import uuid
    
    for emb in embeddings:
        # Create unique Point ID for each angle
        point_id = str(uuid.uuid4())
        
        # Merge base payload with angle info
        payload = base_payload.copy()
        payload["angle"] = emb.get("angle", "front")
        
        points.append(
            PointStruct(
                id=point_id,
                vector={
                    "clip": emb["clip"],
                    "arcface": emb["arcface"]
                },
                payload=payload
            )
        )
    
    get_client().upsert(
        collection_name=QDRANT_COLLECTION,
        points=points
    )

def insert_staff_embedding(staff_id, clip_vector, arcface_vector, payload):
    """Legacy wrapper for single-image registration (backward compatibility)"""
    insert_staff_embeddings_multi(
        staff_id=staff_id,
        embeddings=[{
            "clip": clip_vector,
            "arcface": arcface_vector,
            "angle": "front"
        }],
        base_payload=payload
    )

# ============================
# DELETE STAFF
# ============================

def delete_staff_by_id(staff_id: str):
    """
    Delete all points associated with a staff_id using payload filter.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    get_client().delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="staff_id",
                    match=MatchValue(value=staff_id)
                )
            ]
        )
    )

# ============================
# SEARCH (AUTH / UNAUTH)
# ============================

# PRODUCTION THRESHOLD: Higher value = stricter matching = fewer false positives
# CLIP is not a face recognition model, it compares general visual features
# For production with hundreds of staff, use 0.85+ to allow accurate matching
AUTHORIZATION_THRESHOLD = 0.85  # Optimized for performance

# Minimum score to even consider a match (filters out obvious non-matches)
MINIMUM_CONSIDERATION_SCORE = 0.80

def search_staff_hybrid(
    clip_vector: np.ndarray,
    arcface_vector: np.ndarray = None,
    limit: int = 5
) -> List[dict]:
    """
    Hybrid search: 
    1. Retrieval: Get candidates via CLIP
    2. Reranking: Verify with ArcFace if provided
    """
    try:
        # STEP 1: Search by CLIP
        results = get_client().query_points(
            collection_name=QDRANT_COLLECTION,
            query=clip_vector,
            using="clip",
            limit=limit * 3, # Fetch more to account for multiple angles of same person
            with_payload=True,
            with_vectors=True  # We need vectors for ArcFace comparison
        ).points

        if not results:
            return []

        scored_candidates = []
        seen_staff_ids = set()
        
        for res in results:
            payload = res.payload or {}
            staff_id = payload.get("staff_id")
            
            # Deduplicate by staff_id for the search results
            # We want the best matching angle for each person
            
            clip_score = res.score
            
            # ArcFace cross-check if we have a query face
            arcface_score = 0.0
            if arcface_vector is not None and res.vector and "arcface" in res.vector:
                stored_arcface = np.array(res.vector["arcface"])
                # Cosine similarity
                arcface_score = float(np.dot(arcface_vector, stored_arcface) / (
                    np.linalg.norm(arcface_vector) * np.linalg.norm(stored_arcface) + 1e-6
                ))

            candidate = {
                "staff_id": staff_id,
                "name": payload.get("name"),
                "role": payload.get("role"),
                "department": payload.get("department"),
                "clip_score": round(float(clip_score), 3),
                "arcface_score": round(float(arcface_score), 3),
                "authorized": payload.get("authorized", True),
                "angle": payload.get("angle", "unknown")
            }
            
            scored_candidates.append(candidate)

        # Sort by arcface score if available, else clip
        if arcface_vector is not None:
            scored_candidates.sort(key=lambda x: x["arcface_score"], reverse=True)
        else:
            scored_candidates.sort(key=lambda x: x["clip_score"], reverse=True)
            
        # Deduplicate, keeping the best score for each staff_id
        unique_candidates = []
        seen = set()
        for cand in scored_candidates:
            if cand["staff_id"] not in seen:
                unique_candidates.append(cand)
                seen.add(cand["staff_id"])
        
        return unique_candidates[:limit]
        
    except Exception as e:
        print(f"[QDRANT HYBRID SEARCH ERROR] {e}")
        return []

def search_staff(vector, threshold=None):
    """
    Legacy support - redirected to hybrid search.
    This allows existing code to run during transition.
    """
    results = search_staff_hybrid(vector, limit=1)
    if not results:
        return None
    
    top = results[0]
    # Simple logic for legacy: if clip score high enough
    if top["clip_score"] >= (threshold or AUTHORIZATION_THRESHOLD):
        # Format as expected by legacy search_staff
        return {
            "staff_id": top["staff_id"],
            "name": top["name"],
            "role": top["role"],
            "department": top["department"],
            "score": top["clip_score"],
            "authorized": True,
            "match_quality": "high_confidence"
        }
    return {
        "staff_id": None,
        "name": None,
        "role": None,
        "department": None,
        "score": top["clip_score"],
        "authorized": False,
        "match_quality": "uncertain"
    }



def get_all_staff_count() -> int:
    """Get total count of registered staff for statistics."""
    try:
        collection_info = get_client().get_collection(QDRANT_COLLECTION)
        return collection_info.points_count
    except:
        return 0
