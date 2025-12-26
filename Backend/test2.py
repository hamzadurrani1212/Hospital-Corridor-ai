import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()

print("Opened:", cap.isOpened())
print("Frame OK:", ret)

if ret:
    cv2.imshow("TEST", frame)
    cv2.waitKey(3000)

cap.release()
cv2.destroyAllWindows()
