# client/alerts/alert_sender.py  (async version)
import httpx
import base64
import io
from PIL import Image

TIMEOUT = 5

class AlertSender:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url
        self.client = httpx.AsyncClient(timeout=TIMEOUT)

    async def send(self, payload, snapshot_pil: Image.Image = None):
        if not self.webhook_url:
            return
        # attach snapshot as base64 if provided
        if snapshot_pil is not None:
            buf = io.BytesIO()
            snapshot_pil.save(buf, format="JPEG", quality=70)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            payload["snapshot_b64"] = "data:image/jpeg;base64," + b64

        try:
            resp = await self.client.post(self.webhook_url, json=payload)
            if resp.status_code >= 400:
                print("Alert webhook failed:", resp.status_code, resp.text)
        except Exception as e:
            print("Alert webhook exception:", e)
