# app/routes/embed.py
# from fastapi import APIRouter, UploadFile, File, Form
from fastapi import APIRouter, UploadFile, File, Form
from app.models.clip_embedder import embedder
from app.db.qdrant_client import get_client, QDRANT_COLLECTION
from qdrant_client.models import PointStruct
import uuid
from app.services.preprocessing import load_image_from_bytes


router = APIRouter()

@router.post("/embed/image")
async def embed_image(file: UploadFile = File(...), metadata: str = Form(None)):
    data = await file.read()
    pil = load_image_from_bytes(data)
    vec = embedder.image_embedding(pil).tolist()
    uid = str(uuid.uuid4())
    get_client().upsert(
        collection_name=QDRANT_COLLECTION,
        points=[PointStruct(id=uid, vector=vec, payload={"metadata": metadata})]
    )
    return {"id": uid}

@router.post("/embed/text")
async def embed_text(text: str = Form(...), metadata: str = Form(None)):
    vec = embedder.text_embedding(text).tolist()
    uid = str(uuid.uuid4())
    get_client().upsert(
        collection_name=QDRANT_COLLECTION,
        points=[PointStruct(id=uid, vector=vec, payload={"metadata": metadata})]
    )
    return {"id": uid}
