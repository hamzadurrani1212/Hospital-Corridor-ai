# app/routes/staff.py
"""
Staff management endpoints for authorized personnel registration and lookup.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from PIL import Image
import uuid

from qdrant_client.models import PointIdsList
from app.models.clip_embedder import embedder
from app.services.face_service import face_service
from app.db.qdrant_client import get_client, insert_staff_embedding, QDRANT_COLLECTION
import numpy as np
import cv2

router = APIRouter(prefix="/staff", tags=["Staff Management"])


# ======================================
# REGISTER AUTHORIZED STAFF
# ======================================


# ======================================
# REGISTER AUTHORIZED STAFF
# ======================================

@router.post("/register")
async def register_staff(
    name: str = Form(...),
    role: str = Form(...),
    department: str = Form(...),
    front_image: UploadFile = File(...),
    left_image: Optional[UploadFile] = File(None),
    right_image: Optional[UploadFile] = File(None)
):
    """
    Register authorized hospital staff using 3 face images (Front, Left, Right).
    """

    # Helper to process an image and get embeddings
    def process_image(upload_file, angle_name):
        if not upload_file:
            return None
            
        try:
            img = Image.open(upload_file.file).convert("RGB")
        except Exception:
            return None # Skip invalid images

        # Step 1: Detect face and get ArcFace embedding
        cv2_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        face_details = face_service.get_face_details(cv2_img)
        
        if not face_details:
             # Skip if no face found in this angle
             return None

        arcface_vector = face_details["embedding"].tolist()
        clip_vector = embedder.image_embedding(img).tolist()
        
        return {
            "clip": clip_vector,
            "arcface": arcface_vector,
            "angle": angle_name
        }

    # Process all provided images
    embeddings = []
    
    # Front is mandatory-ish, but if it fails we might still have others. 
    # But usually front is best. Let's process all and check if we have at least one.
    
    front_emb = process_image(front_image, "front")
    if front_emb: embeddings.append(front_emb)
    
    if left_image:
        left_emb = process_image(left_image, "left")
        if left_emb: embeddings.append(left_emb)
        
    if right_image:
        right_emb = process_image(right_image, "right")
        if right_emb: embeddings.append(right_emb)
        
    if not embeddings:
         raise HTTPException(
            status_code=400,
            detail="No face detected in any of the uploaded images. Please upload clear photos."
        )

    # Generate unique staff ID shared by all angles
    staff_id = str(uuid.uuid4())

    # Store in Qdrant (all angles)
    from app.db.qdrant_client import insert_staff_embeddings_multi
    
    insert_staff_embeddings_multi(
        staff_id=staff_id,
        embeddings=embeddings,
        base_payload={
            "staff_id": staff_id,
            "name": name,
            "role": role,
            "department": department,
            "authorized": True
        }
    )

    return {
        "status": "success",
        "message": f"Authorized staff registered with {len(embeddings)} angles",
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
    Deduplicates multiple angles to return unique staff list.
    """
    try:
        # Get all points from the collection
        result = get_client().scroll(
            collection_name=QDRANT_COLLECTION,
            limit=1000, # Increased limit to get all points
            with_payload=True,
            with_vectors=False
        )
        
        # Deduplicate by staff_id
        staff_map = {}
        
        for point in result[0]:
            payload = point.payload or {}
            staff_id = payload.get("staff_id")
            
            if staff_id and staff_id not in staff_map:
                staff_map[staff_id] = {
                    "id": staff_id, # return staff_id as the main id
                    "staff_id": staff_id,
                    "name": payload.get("name"),
                    "role": payload.get("role"),
                    "department": payload.get("department"),
                    "authorized": payload.get("authorized", False),
                    "angles_count": 1
                }
            elif staff_id:
                staff_map[staff_id]["angles_count"] += 1
        
        return list(staff_map.values())
        
    except Exception as e:
        print(f"List staff error: {e}")
        return []


@router.get("/{staff_id}")
async def get_staff(staff_id: str):
    """
    Get a specific staff member by ID.
    Deduplicates logic here implies we just need one point to get metadata.
    """
    try:
        # Search by payload filter instead of ID since ID is random now
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        result = get_client().scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="staff_id",
                        match=MatchValue(value=staff_id)
                    )
                ]
            ),
            limit=1,
            with_payload=True
        )
        
        points = result[0]
        if not points:
             raise HTTPException(status_code=404, detail="Staff not found")
             
        point = points[0]
        payload = point.payload or {}
        
        return {
            "id": staff_id,
            "staff_id": staff_id,
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
    Remove an authorized staff member (all angles).
    """
    try:
        from app.db.qdrant_client import delete_staff_by_id
        delete_staff_by_id(staff_id)
        return {"status": "deleted", "staff_id": staff_id}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete: {str(e)}")

