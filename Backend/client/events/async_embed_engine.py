import asyncio
from app.models.clip_embedder import embedder  # your existing CLIP embedder
from app.db.qdrant_client import qdrant        # your Qdrant client

class AsyncEmbedEngine:
    """
    Async non-blocking background engine which:
      - Accepts cropped person images
      - Sends them to /api/embed (FastAPI endpoint)
      - Upserts vectors to Qdrant on server side
    """

    def __init__(self, embed_endpoint: str):
        self.embed_endpoint = embed_endpoint
        self.queue = asyncio.Queue()
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            try:
                item = await self.queue.get()
                if item is None:
                    break
                await self._process(item)
            except Exception as e:
                print("Embedding error:", e)

    async def _process(self, item):
        """
        item = {
            "image": PIL.Image,
            "file_name": str
        }
        """
        vec = embedder.image_embedding(item["image"])  # synchronous; if async CLIP available, await it
        uid = str(item.get("id") or uuid.uuid4())
        # Qdrant upsert can be async if using async client; here we just wrap in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, qdrant.upsert, uid, vec.tolist(), {"source":"detect","file":item["file_name"]})

    async def enqueue(self, image, file_name, id=None):
        await self.queue.put({"image": image, "file_name": file_name, "id": id})

    async def stop(self):
        self.running = False
        await self.queue.put(None)
