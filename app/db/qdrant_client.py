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

def search_staff(
    vector,
    threshold: float = 0.82
) -> Optional[dict]:
    """
    Search for similar authorized staff

    Returns:
        {
            staff_id,
            name,
            role,
            department,
            score
        }
        OR None if unauthorized
    """

    results = get_client().query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector,
        limit=1
    ).points

    if not results:
        return None

    top = results[0]
    print(f"[QDRANT RAW] ID: {top.id} Score: {top.score:.4f} Payload: {top.payload}")
    print(f"[AUTH TRY] Best score: {top.score:.4f} vs Threshold: {threshold}")
    
    if top.score >= threshold:
        payload = top.payload or {}
        return {
            "staff_id": payload.get("staff_id"),
            "name": payload.get("name"),
            "role": payload.get("role"),
            "department": payload.get("department"),
            "score": round(top.score, 3),
            "authorized": True
        }

    return None
