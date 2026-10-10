import cv2
import numpy as np
import os
import time
import json
from datetime import datetime

# Camera and output folder
CAMERA = "/dev/video0"
PHOTO_DIR = os.path.expanduser("~/roadbot/photos")

# Manual location
LATITUDE = 10.7735
LONGITUDE = 76.3775

# Detection tuning
MIN_RED_AREA = 500
BOX_THICKNESS = 1
STABLE_FRAMES = 3
MATCH_DISTANCE = 140
TRACK_TIMEOUT = 3.0

os.makedirs(PHOTO_DIR, exist_ok=True)

camera = cv2.VideoCapture(CAMERA)

if not camera.isOpened():
    print("ERROR: Camera could not open")
    raise SystemExit(1)

lower1 = np.array([0, 100, 100])
upper1 = np.array([10, 255, 255])
lower2 = np.array([160, 100, 100])
upper2 = np.array([179, 255, 255])

kernel = np.ones((5, 5), np.uint8)
tracks = []
next_id = 1

print("Red-region tracking started.")
print("Press Ctrl+C to stop.")

try:
    while True:
        ok, frame = camera.read()

        if not ok:
            time.sleep(0.1)
            continue

        now_time = time.time()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask = cv2.bitwise_or(
            cv2.inRange(hsv, lower1, upper1),
            cv2.inRange(hsv, lower2, upper2)
        )

        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, kernel
        )

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        detections = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < MIN_RED_AREA:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            detections.append({
                "box": (x, y, w, h),
                "center": (x + w // 2, y + h // 2)
            })

        # Expire old tracks
        tracks = [
            t for t in tracks
            if now_time - t["last_seen"] < TRACK_TIMEOUT
        ]

        used_ids = set()
        new_tracks = []

        for det in detections:
            x, y, w, h = det["box"]
            cx, cy = det["center"]

            best_track = None
            best_distance = MATCH_DISTANCE

            # Match this region to a previously tracked region
            for track in tracks:
                if track["id"] in used_ids:
                    continue

                tx, ty = track["center"]
                distance = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5

                if distance < best_distance:
                    best_distance = distance
                    best_track = track

            if best_track is not None:
                best_track["center"] = (cx, cy)
                best_track["last_seen"] = now_time
                best_track["count"] += 1
                used_ids.add(best_track["id"])
                track = best_track
            else:
                track = {
                    "id": next_id,
                    "center": (cx, cy),
                    "last_seen": now_time,
                    "count": 1,
                    "saved": False
                }
                next_id += 1
                new_tracks.append(track)
                used_ids.add(track["id"])

            x, y, w, h = det["box"]

            # Thin rectangle and crack label
            cv2.rectangle(
                frame, (x, y), (x + w, y + h),
                (0, 255, 0), BOX_THICKNESS
            )

            cv2.putText(
                frame, "CRACK DETECTED",
                (x, max(y - 8, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0, 255, 0), 1
            )

            # Save once after the region is stable
            if track["count"] >= STABLE_FRAMES and not track["saved"]:
                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                filename = os.path.join(
                    PHOTO_DIR,
                    f"crack_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                )

                if cv2.imwrite(filename, frame):
                    report = {
                        "detection": "CRACK DETECTED",
                        "latitude": LATITUDE,
                        "longitude": LONGITUDE,
                        "timestamp": timestamp,
                        "photo": filename
                    }

                    report_file = os.path.splitext(filename)[0] + ".json"
                    with open(report_file, "w") as f:
                        json.dump(report, f, indent=4)

                    track["saved"] = True
                    print("New region photo:", filename)
                    print("Location:", LATITUDE, LONGITUDE)
                    print("Report:", report_file)

        tracks.extend(new_tracks)
        time.sleep(0.03)

except KeyboardInterrupt:
    print("\nDetection stopped.")

finally:
    camera.release()
    print("Camera released.")
