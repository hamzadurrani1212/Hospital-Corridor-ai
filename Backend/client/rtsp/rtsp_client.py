# Import required libraries
from PIL import Image  # For image processing
import cv2  # OpenCV for computer vision and camera handling
import asyncio  # For asynchronous programming
import httpx  # Async HTTP client for API calls (still needed for embeddings)
import time  # For timing operations

# Import local YOLO detector
from client.models.yolo_detector import YOLODetector

# Configuration constants
POST_INTERVAL = 0.5  # Send frames to server every 0.5 seconds
MAX_RETRIES = 3  # Maximum retries for HTTP requests (for embeddings)
TIMEOUT = 10  # HTTP request timeout in seconds
RECONNECT_DELAY = 5  # Delay between reconnection attempts


class RTSPClient:
    """
    Main RTSP client class for handling camera streams
    Connects to RTSP cameras, processes frames with local YOLO detection
    """
    
    def __init__(
        self,
        rtsp_url,  # RTSP stream URL or webcam index
        server_url,  # Backend API URL for embeddings (optional)
        event_engine=None,  # Optional event processing engine
        frame_skip_rate=1,  # Process every Nth frame
        camera_name=None,  # Custom camera name
        show_live=False,  # Whether to display live feed
    ):
        # Store configuration parameters
        self.rtsp_url = rtsp_url
        self.server_url = server_url  # Still used for embedding API calls
        self.event_engine = event_engine
        self.stop_flag = False  # Control flag for stopping the client
        
        # Initialize local YOLO detector
        self.detector = YOLODetector()  #  LOCAL YOLO DETECTOR
        print(f"{camera_name or 'Camera'}:  YOLO detector initialized")

        # Frame processing configuration
        self.frame_skip_rate = max(1, frame_skip_rate)  # Ensure at least 1
        self.camera_name = camera_name or self._extract_camera_name(rtsp_url)
        self.show_live = show_live

        # Performance tracking
        self.frame_counter = 0  # Total frames read
        self.processed_frame_counter = 0  # Frames processed locally

        # Initialize placeholders (set later)
        self.client = None  # HTTP client instance (still needed for embeddings)
        self.cap = None  # OpenCV video capture object

    def _extract_camera_name(self, url):
        """
        Extract a readable camera name from RTSP URL
        Example: rtsp://user:pass@192.168.1.12:554/stream → Camera_192.168.1.12
        """
        try:
            if "@" in url:  # Check if URL has authentication
                # Extract host/IP address after @ symbol
                host = url.split("@")[1].split("/")[0].split(":")[0]
                return f"Camera_{host}"
        except Exception:
            pass  # If extraction fails, return default name
        return "Unknown_Camera"  # Default name if extraction fails

    async def _initialize_capture(self):
        """
        Initialize and connect to the camera stream
        Returns: True if connection successful, False otherwise
        """
        try:
            # Log connection attempt
            print(f"{self.camera_name}: 🔗 Connecting to {self.rtsp_url}")

            # Create video capture object using FFMPEG backend
            # FFMPEG is better for RTSP streams than default backend
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)

            # CRITICAL: Configure OpenCV for better RTSP performance
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer to reduce latency
            cap.set(cv2.CAP_PROP_FPS, 15)  # Set expected frame rate
            # Set codec to MJPEG for better compatibility
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

            # Set timeout parameters to prevent hanging
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 30000)  # 30 second connection timeout
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)  # 10 second read timeout

            # Wait for connection to establish
            await asyncio.sleep(1)

            # Check if camera opened successfully
            if cap.isOpened():
                # Test if we can actually read a frame
                ret, test_frame = cap.read()
                if ret and test_frame is not None:
                    print(f"{self.camera_name}:  Successfully connected")
                    self.cap = cap  # Store the capture object
                    return True
                else:
                    # Camera opened but can't read frames (may be permissions/format issue)
                    print(f"{self.camera_name}: ⚠ Connected but can't read frames")
                    cap.release()  # Clean up
            else:
                # Camera failed to open (network/auth/URL issue)
                print(f"{self.camera_name}:  Failed to open stream")

            return False  # Connection failed

        except Exception as e:
            # Handle any exceptions during initialization
            print(f"{self.camera_name}:  Capture init error: {e}")
            return False

    async def start(self):
        """
        Main processing loop - runs indefinitely until stop_flag is True
        Handles frame capture, local YOLO processing, and server communication for embeddings
        """
        # Initialize HTTP client for embedding API calls (if needed)
        self.client = httpx.AsyncClient(timeout=TIMEOUT)

        retry_count = 0  # Track reconnection attempts
        max_retries = 5  # Maximum reconnection attempts before giving up

        # Main reconnection loop
        while not self.stop_flag and retry_count < max_retries:
            try:
                # Attempt to connect to camera
                connected = await self._initialize_capture()

                if not connected:
                    # Connection failed, increment retry counter
                    retry_count += 1
                    print(f"{self.camera_name}:  Connection failed ({retry_count}/{max_retries})")
                    await asyncio.sleep(RECONNECT_DELAY)  # Wait before retrying
                    continue  # Try again

                # Connection successful - reset retry counter
                print(f"{self.camera_name}:  Starting frame processing with local YOLO...")
                retry_count = 0  # Reset on success

                # Performance tracking variables
                last_post = 0  # Timestamp of last frame processed
                fps_counter = 0  # Count frames for FPS calculation
                fps_start_time = time.time()  # Start time for FPS calculation

                # Main frame processing loop
                while not self.stop_flag and self.cap is not None:
                    # Read a frame from the camera
                    ret, frame = self.cap.read()

                    if not ret or frame is None:
                        # Frame read failed - connection may be lost
                        print(f"{self.camera_name}: ⚠ Lost connection, reconnecting...")
                        break  # Exit inner loop to reconnect

                    # Optionally display live feed (for debugging/monitoring)
                    if self.show_live:
                        try:
                            # Resize for consistent display size
                            display_frame = cv2.resize(frame, (640, 480))
                            # Show frame in window named after camera
                            cv2.imshow(self.camera_name, display_frame)
                            # Check if 'q' key is pressed to quit
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                self.stop_flag = True  # Set stop flag
                                break
                        except Exception as e:
                            print(f"{self.camera_name}: ⚠ Display error: {e}")

                    # Increment total frame counter
                    self.frame_counter += 1

                    # Apply frame skipping - only process every Nth frame
                    if self.frame_counter % self.frame_skip_rate != 0:
                        await asyncio.sleep(0.001)  # Small yield to prevent CPU hogging
                        continue  # Skip this frame

                    # Check if it's time to process frame (throttle processing)
                    now = time.time()
                    if now - last_post >= POST_INTERVAL:
                        #  LOCAL YOLO DETECTION (replaces API call)
                        # Run YOLO detection directly on the frame
                        detections = self.detector.detect(frame)
                        
                        # Optional: Draw detections on frame for display
                        if self.show_live and detections:
                            # Create a copy for display with bounding boxes
                            display_frame_with_boxes = frame.copy()
                            for det in detections:
                                # Extract detection info
                                x1, y1, x2, y2 = map(int, det.get('bbox', [0, 0, 0, 0]))
                                label = det.get('class', 'unknown')
                                confidence = det.get('confidence', 0)
                                
                                # Draw bounding box
                                cv2.rectangle(display_frame_with_boxes, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                # Draw label with confidence
                                label_text = f"{label}: {confidence:.2f}"
                                cv2.putText(display_frame_with_boxes, label_text, (x1, y1 - 10),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
                            # Update display window with detection boxes
                            if self.show_live:
                                display_frame_resized = cv2.resize(display_frame_with_boxes, (640, 480))
                                cv2.imshow(self.camera_name, display_frame_resized)

                        # Process detections if we have an event engine
                        if detections and self.event_engine:
                            try:
                                # Convert BGR (OpenCV) to RGB (PIL) format
                                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                # Convert to PIL Image for event processing
                                frame_pil = Image.fromarray(frame_rgb)

                                # Send to event engine for anomaly detection
                                await self.event_engine.process_frame(
                                    detections,  # Detected objects from local YOLO
                                    frame_pil,   # Original image
                                    now,         # Timestamp
                                )
                            except Exception as e:
                                print(f"{self.camera_name}: ⚠ Event processing error: {e}")

                        # Update timing and counters
                        last_post = now  # Update last processed time
                        self.processed_frame_counter += 1  # Increment processed count
                        fps_counter += 1  # Increment FPS counter
                        
                        # Optional: Log detection count periodically
                        if detections and self.processed_frame_counter % 10 == 0:
                            print(f"{self.camera_name}: 🔍 Detected {len(detections)} objects")

                        # Calculate and display FPS periodically
                        if fps_counter >= 20:  # Every 20 processed frames
                            elapsed = time.time() - fps_start_time
                            if elapsed > 0:
                                fps = fps_counter / elapsed  # Calculate FPS
                                print(f"{self.camera_name}: 📊 FPS = {fps:.1f} (Total: {self.processed_frame_counter})")
                            # Reset counters
                            fps_counter = 0
                            fps_start_time = time.time()

                    # Small sleep to prevent CPU hogging
                    await asyncio.sleep(0.001)

            except Exception as e:
                # Handle errors in main processing loop
                retry_count += 1
                print(f"{self.camera_name}: ❌ Error: {type(e).__name__}: {e}")
                await asyncio.sleep(RECONNECT_DELAY)  # Wait before retrying

            finally:
                # Cleanup resources after loop ends (error or normal exit)
                await self._cleanup_capture()

        # Check if we exceeded maximum reconnection attempts
        if retry_count >= max_retries:
            print(f"{self.camera_name}: ❌ Max reconnection attempts reached")

        # Final cleanup
        await self.stop()

    async def _cleanup_capture(self):
        """
        Clean up camera resources
        Releases video capture and closes display windows
        """
        if self.cap is not None:
            self.cap.release()  # Release camera resource
            self.cap = None  # Clear reference

        if self.show_live:
            try:
                cv2.destroyWindow(self.camera_name)  # Close display window
            except:
                pass  # Ignore if window doesn't exist

    async def _post_frame(self, data):
        """
        DEPRECATED: This method is no longer needed for detection
        Kept for backward compatibility or for sending embeddings
        """
        print(f"{self.camera_name}: ⚠ _post_frame called but detection is now local")
        return None

    async def stop(self):
        """
        Gracefully stop the RTSP client
        Cleans up all resources and connections
        """
        self.stop_flag = True  # Signal to stop all loops

        await self._cleanup_capture()  # Cleanup camera resources

        # Cleanup YOLO detector if it has cleanup method
        if hasattr(self.detector, 'cleanup'):
            self.detector.cleanup()

        # Close HTTP client if it exists
        if self.client:
            await self.client.aclose()  # Async close
            self.client = None  # Clear reference

        print(f"{self.camera_name}:  Stopped")  # Log stop message
