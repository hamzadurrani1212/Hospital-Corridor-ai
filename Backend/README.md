# Hospital Corridor Safety Monitor

An AI-powered computer vision system designed to monitor hospital corridors for safety events such as falls, patient immobility, and overcrowding. The system utilizes **YOLOv8** for detection, **CLIP** for semantic embedding, and **Qdrant** for vector search, coupled with a specific **FastAPI** backend and a **Next.js** dashboard.

##  Key Features

- **Real-time Monitoring**: Processes video feeds from RTSP cameras or local webcams.
- **Fall & Immobility Detection**:
  - **No Movement**: Alerts if a person remains stationary for over 20 seconds.
  - **Possible Lying**: Detects unusual aspect ratios indicative of a fall.
- **Crowd Detection**: Automatically flags frames with high person density (default > 4 people).
- **Semantic Search**: Search for specific people or events using text descriptions or reference images (powered by CLIP + Qdrant).
- **Live Dashboard**: Web-based interface for viewing live alerts, system health, and camera feeds.

##  System Architecture

The project is divided into three main components:

1.  **Backend (`/app`)**:
    - Built with **FastAPI**.
    - Handles API requests, WebSocket connections for alerts, and communicates with the Vector Database.
    - Manages snapshot storage for alert evidence.

2.  **Vision Client (`/client`)**:
    - Built with **Python** & **OpenCV**.
    - Runs the logic loop: Capture Frame -> YOLO Detection -> Tracking -> Event Logic -> API/Alert Submission.
    - Handles the "edge" processing.

3.  **Frontend (`/frontend`)**:
    - Built with **Next.js 16**, **React 19**, and **TailwindCSS 4**.
    - Provides a modern UI for hospital staff to monitor alerts and system status.

---

##  Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Qdrant** (Vector Database) - Cloud instance or Local Docker container running on port 6333.
- **CUDA** (Recommended for GPU acceleration with YOLO/CLIP).

---

##  Installation & Setup

### 1. Backend Setup

```bash
# Navigate to the root directory
cd c:\hospital-corridor-ai

# Activate your virtual environment (if using one)
# .\myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Client Setup

The client shares dependencies with the backend. Ensure you have the camera source configured.

- Edit `client/main.py` to set up your camera:
  ```python
  # For Webcam
  WEBCAMS = [0]
  
  # For RTSP
  # WEBCAMS = ["rtsp://user:pass@ip:port/stream"]
  ```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

---

## ▶ Usage Guide

To run the full system, you need three terminals:

**Terminal 1: Start the Backend**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*Server runs at http://localhost:8000*

**Terminal 2: Start the Frontend**
```bash
cd frontend
npm run dev
```
*Dashboard runs at http://localhost:3000*

**Terminal 3: Start the Vision Client**
```bash
python -m client.main
```
*This will open a CV2 window showing the live feed with bounding boxes and send alerts to the backend.*

---

##  AI Models Used

- **YOLOv8** (Large/Medium): For robust person detection.
- **CLIP** (OpenAI/ViT): For generating vector embeddings of detected people to enable semantic search.
- **SimpleTracker**: A centroid-based tracker to maintain identity across frames (located in `client/tracker`).

##  Configuration

- **Environment Variables**: Check `.env` files for Qdrant API keys and URLs.
- **Thresholds**: Adjust `CROWD_THRESHOLD`, `NO_MOVE_SECONDS`, and `MOVEMENT_PIXEL_THRESHOLD` in `client/events/event_engine.py` to tune sensitivity.

