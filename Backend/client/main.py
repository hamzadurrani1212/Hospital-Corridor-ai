import cv2
import asyncio
import signal
from client.rtsp.rtsp_client import RTSPClient
from client.events.event_engine import EventEngine
from client.alerts.alert_sender import AlertSender
from client.events.async_embed_engine import AsyncEmbedEngine

# -----------------------------
# CAMERA CONFIG - WEB CAMERA FIRST
# -----------------------------
#  Use plain integers for webcams
WEBCAMS = [   0   ]  # Default webcam

# For RTSP cameras (example):
# WEBCAMS = [
#     "rtsp://hamza-durrani:1122@192.168.1.12:554/stream",
#     "rtsp://hamza-durrani:1122@192.168.1.15:554/stream",
# ]

SERVER_URL = "http://localhost:8000/api/detect"
ALERT_WEBHOOK = None

# -----------------------------
# WEB CAMERA CLIENT
# -----------------------------

class WebcamClient(RTSPClient):
    """Modified RTSPClient for local webcams"""

    def _extract_camera_name(self, camera_id):
        if isinstance(camera_id, int):
            return f"Webcam_{camera_id}"
        elif isinstance(camera_id, str) and camera_id.endswith(('.mp4', '.avi', '.mov')):
            return f"Video_{camera_id.split('/')[-1]}"
        return f"Camera_{camera_id}"

    async def _initialize_capture(self):

        try:
            print(f"{self.camera_name}:  Connecting using index={self.rtsp_url}")

            #  CAP_DSHOW prevents webcam freeze on Windows
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_DSHOW)

            if not cap.isOpened():
                print(f"{self.camera_name}:  Cannot open device")
                return False

            ret, test_frame = cap.read()

            if not ret or test_frame is None:
                print(f"{self.camera_name}:  Opened but no frames")
                cap.release()
                return False

            print(
                f"{self.camera_name}:  OPENED "
                f"RES={test_frame.shape[1]}x{test_frame.shape[0]}"
            )

            self.cap = cap
            return True

        except Exception as e:
            print(f"{self.camera_name}:  INIT ERROR: {e}")
            return False

# -----------------------------
# MAIN
# -----------------------------

async def main():

    print(" Initializing Hospital Corridor Safety Monitor...")
    print(" Using LOCAL WEBCAM for testing")
    print("  Make sure FastAPI backend is running on http://localhost:8000")

    # -----------------------------
    # CHECK BACKEND
    # -----------------------------
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/docs", timeout=5)

            if response.status_code == 200:
                print(" Backend server is Running")
            else:
                print(f"⚠ Backend responded with status: {response.status_code}")

    except Exception as e:
        print(f" Cannot reach backend server: {e}")
        print(" Run backend first: uvicorn app.main:app --reload")
        return

    # -----------------------------
    # ALERT SENDER
    # -----------------------------
    alert_sender = None
    if ALERT_WEBHOOK:
        try:
            alert_sender = AlertSender(ALERT_WEBHOOK)
            print(" Alert sender initialized")
        except Exception as e:
            print(f"⚠ Alert sender failed: {e}")

    # -----------------------------
    # EMBED ENGINE
    # -----------------------------
    embed_engine = None
    try:
        embed_engine = AsyncEmbedEngine("http://localhost:8000/api/embed")
        asyncio.create_task(embed_engine.start())  #  run in background
        
        print(" Embedding engine started")
    except Exception as e:
        print(f"⚠ Embedding engine failed: {e}")
        embed_engine = None

    # -----------------------------
    # EVENT ENGINE
    # -----------------------------
    event_engine = None
    try:
        event_engine = EventEngine(
            alert_sender=alert_sender,
            embed_engine=embed_engine
        )
        print(" Event engine initialized")
    except Exception as e:
        print(f"⚠ Event engine failed: {e}")

    # -----------------------------
    # CREATE CAMERA CLIENTS
    # -----------------------------
    clients = []

    for i, cam_id in enumerate(WEBCAMS):
        try:
            print(f"\n Initializing Webcam {i + 1}")

            client = WebcamClient(
                rtsp_url=cam_id,
                server_url=SERVER_URL,
                event_engine=event_engine,
                show_live=True,
                frame_skip_rate=2,
                camera_name=f"Webcam_{i+1}"
            )

            clients.append(client)
            print("    Webcam client created")

        except Exception as e:
            print(f"    Failed creating client: {e}")

    if not clients:
        print(" No webcams initialized. Exiting.")
        return

    print(f"\n Starting {len(clients)} webcam stream(s)...")
    print("=" * 50)
    print("CONTROLS:")
    print("- Press 'q' inside any window to stop that stream")
    print("- Press Ctrl+C to stop everything")
    print("=" * 50)

    # -----------------------------
    # SHUTDOWN SIGNALS
    # -----------------------------
    def signal_handler(sig, frame):
        print("\n Signal received, stopping cameras...")
        for client in clients:
            client.stop_flag = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # -----------------------------
    # START STREAMS
    # -----------------------------
    try:
        tasks = [client.start() for client in clients]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, r in enumerate(results):
            if isinstance(r, Exception):
                print(f" Webcam {i+1} error: {r}")

    except KeyboardInterrupt:
        print("\n Keyboard interrupt")
    except Exception as e:
        print(f"\n Unexpected main error: {e}")

    finally:
        print("\n Shutting down system...")

        for client in clients:
            try:
                await client.stop()
            except:
                pass

        if embed_engine:
            try:
                await embed_engine.stop()
            except:
                pass

        cv2.destroyAllWindows()
        print(" Shutdown completed")

# -----------------------------
# ENTRY
# -----------------------------

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Forced exit")
    except Exception as e:
        print(f"\n Critical startup error: {e}")
