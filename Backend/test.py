import cv2
import time

cameras = [
    "rtsp://hamza-durrani:1122@192.168.1.12:554/stream",
    "rtsp://hamza-durrani:1122@192.168.1.15:554/stream",
]

for i, url in enumerate(cameras):
    print(f"\nTesting Camera {i+1}: {url}")
    
    # Try with different OpenCV parameters
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Wait a bit
    time.sleep(2)
    
    if cap.isOpened():
        print(f"  ✓ Camera opened successfully")
        
        # Try to read a frame
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"  ✓ Frame read successfully: {frame.shape}")
            
            # Show frame briefly
            cv2.imshow(f"Camera {i+1}", frame)
            cv2.waitKey(1000)  # Show for 1 second
            cv2.destroyAllWindows()
        else:
            print(f"  ✗ Could not read frame")
        
        cap.release()
    else:
        print(f"  ✗ Failed to open camera")