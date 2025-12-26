from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from typing import Optional

# ============================
# QDRANT CONFIG
# ============================

QDRANT_COLLECTION = "authorized_staff"

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
                vectors_config=VectorParams(
                    size=512,              # CLIP ViT-B/32
                    distance=Distance.COSINE
                )
            )
            print(f"[QDRANT] Collection '{QDRANT_COLLECTION}' created")
        else:
            print(f"[QDRANT] Collection '{QDRANT_COLLECTION}' already exists")
    except Exception as e:
        print(f"[QDRANT INIT ERROR] {e}")

# ============================
# INSERT AUTHORIZED STAFF
# ============================

def insert_staff_embedding(
    staff_id: str,
    vector,
    payload: dict
):
    """
    Insert or update authorized staff embedding
    """
    get_client().upsert(
        collection_name=QDRANT_COLLECTION,
        points=[
            PointStruct(
                id=staff_id,
                vector=vector,
                payload=payload
            )
        ]
    )

# ============================
# SEARCH (AUTH / UNAUTH)
# ============================

# PRODUCTION THRESHOLD: Higher value = stricter matching = fewer false positives
# CLIP is not a face recognition model, it compares general visual features
# For production with hundreds of staff, use 0.92+ to avoid misidentification
AUTHORIZATION_THRESHOLD = 0.92  # Increased from 0.81 for production accuracy

# Minimum score to even consider a match (filters out obvious non-matches)
MINIMUM_CONSIDERATION_SCORE = 0.85

def search_staff(
    vector,
    threshold: float = None
) -> Optional[dict]:
    """
    Search for authorized staff with strict matching for production use.
    
    IMPORTANT FOR PRODUCTION:
    - Only returns authorized=True if score >= 0.92 (very high confidence)
    - This prevents misidentifying Person A as Person B in a large database
    - If a person is deleted from DB, their detection will show UNAUTHORIZED
    
    Args:
        vector: CLIP embedding of detected person
        threshold: Override threshold (default uses AUTHORIZATION_THRESHOLD)
    
    Returns:
        dict with staff info if authorized, or minimal dict if not
    """
    if threshold is None:
        threshold = AUTHORIZATION_THRESHOLD
    
    try:
        results = get_client().query_points(
            collection_name=QDRANT_COLLECTION,
            query=vector,
            limit=1
        ).points

        if not results:
            # No staff in database at all
            return None

        top = results[0]
        score = top.score
        payload = top.payload or {}
        
        # STEP 1: Check if score even worth considering
        if score < MINIMUM_CONSIDERATION_SCORE:
            # Score too low to be the same person - definitely unauthorized
            return {
                "staff_id": None,
                "name": None,
                "role": None,
                "department": None,
                "score": round(score, 3),
                "authorized": False,
                "match_quality": "no_match"
            }
        
        # STEP 2: Check if score meets authorization threshold
        if score < threshold:
            # Score is between 0.85-0.92: possible match but not confident enough
            # For safety, mark as UNAUTHORIZED (don't show other person's name)
            return {
                "staff_id": None,
                "name": None,
                "role": None,
                "department": None,
                "score": round(score, 3),
                "authorized": False,
                "match_quality": "uncertain"  # Close but not confident enough
            }
        
        # STEP 3: High confidence match - AUTHORIZED
        # Score >= 0.92 means we're very confident this is the same person
        return {
            "staff_id": payload.get("staff_id"),
            "name": payload.get("name"),
            "role": payload.get("role"),
            "department": payload.get("department"),
            "score": round(score, 3),
            "authorized": True,
            "match_quality": "high_confidence"
        }
        
    except Exception as e:
        print(f"[QDRANT SEARCH ERROR] {e}")
        return None


def get_all_staff_count() -> int:
    """Get total count of registered staff for statistics."""
    try:
        collection_info = get_client().get_collection(QDRANT_COLLECTION)
        return collection_info.points_count
    except:
        return 0
