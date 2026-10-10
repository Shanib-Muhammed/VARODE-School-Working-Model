import cv2
import numpy as np
import os
import time

CAMERA = "/dev/video0"
PHOTO_DIR = os.path.expanduser("~/roadbot/photos")

MIN_RED_AREA = 500

os.makedirs(PHOTO_DIR, exist_ok=True)

camera = cv2.VideoCapture(CAMERA)

if not camera.isOpened():
    print("ERROR: Camera could not open")
    raise SystemExit(1)

lower1 = np.array([0, 100, 100])
upper1 = np.array([10, 255, 255])
lower2 = np.array([160, 100, 100])
upper2 = np.array([179, 255, 255])

red_was_present = False

print("Red detection with bounding boxes started.")
print("Press Ctrl+C to stop.")

try:
    while True:
        ok, frame = camera.read()

        if not ok:
            print("Cannot read camera frame")
            time.sleep(1)
            continue

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Remove small colour noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, kernel
        )

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        red_found = False

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < MIN_RED_AREA:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            # Draw a box around each detected red region
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "RED DETECTED",
                (x, max(y - 10, 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

            red_found = True

        # Save one photo when red first appears
        if red_found and not red_was_present:
            filename = os.path.join(
                PHOTO_DIR,
                f"red_{int(time.time())}.jpg"
            )

            if cv2.imwrite(filename, frame):
                print("Red detected. Boxed photo saved:", filename)

        red_was_present = red_found

        # No live camera window is opened
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nDetection stopped.")

finally:
    camera.release()
