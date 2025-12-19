# app/routes/staff.py
"""
Staff management endpoints for authorized personnel registration and lookup.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import uuid

from qdrant_client.models import PointIdsList
from app.models.clip_embedder import embedder
from app.models.clip_embedder import embedder
from app.db.qdrant_client import get_client, insert_staff_embedding, QDRANT_COLLECTION

router = APIRouter(prefix="/staff", tags=["Staff Management"])


# ======================================
# REGISTER AUTHORIZED STAFF
# ======================================

@router.post("/register")
async def register_staff(
    name: str = Form(...),
    role: str = Form(...),
    department: str = Form(...),
    image: UploadFile = File(...)
):
    """
    Register authorized hospital staff using face image.
    The image is converted to a CLIP embedding and stored in Qdrant.
    """

    # Validate image type
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG images are allowed"
        )

    try:
        img = Image.open(image.file).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file"
        )

    # Generate CLIP embedding
    vector = embedder.image_embedding(img)

    # Generate unique staff ID
    staff_id = str(uuid.uuid4())

    # Store in Qdrant
    insert_staff_embedding(
        staff_id=staff_id,
        vector=vector,
        payload={
            "staff_id": staff_id,
            "name": name,
            "role": role,
            "department": department,
            "authorized": True
        }
    )

    return {
        "status": "success",
        "message": "Authorized staff registered",
        "staff_id": staff_id,
        "name": name,
        "role": role,
        "department": department
    }


# ======================================
# LIST STAFF
# ======================================

@router.get("/")
async def list_staff():
    """
    List all registered authorized staff.
    """
    try:
        # Get all points from the collection
        result = get_client().scroll(
            collection_name=QDRANT_COLLECTION,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        staff_list = []
        for point in result[0]:  # result is (points, next_page_offset)
            payload = point.payload or {}
            staff_list.append({
                "id": str(point.id),
                "staff_id": payload.get("staff_id"),
                "name": payload.get("name"),
                "role": payload.get("role"),
                "department": payload.get("department"),
                "authorized": payload.get("authorized", False)
            })
        
        return staff_list
        
    except Exception as e:
        return []


@router.get("/{staff_id}")
async def get_staff(staff_id: str):
    """
    Get a specific staff member by ID.
    """
    try:
        result = get_client().retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=[staff_id],
            with_payload=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Staff not found")
        
        point = result[0]
        payload = point.payload or {}
        
        return {
            "id": str(point.id),
            "staff_id": payload.get("staff_id"),
            "name": payload.get("name"),
            "role": payload.get("role"),
            "department": payload.get("department"),
            "authorized": payload.get("authorized", False)
        }
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Staff not found")


# ======================================
# DELETE STAFF
# ======================================

@router.delete("/{staff_id}")
async def delete_staff(staff_id: str):
    """
    Remove an authorized staff member.
    """
    try:
        get_client().delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=PointIdsList(points=[staff_id])
        )
        return {"status": "deleted", "staff_id": staff_id}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete: {str(e)}")
