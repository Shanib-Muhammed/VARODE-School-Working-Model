import cv2
import numpy as np
import os
import time
import json
import requests
from datetime import datetime, timezone

# ==================================================
# CAMERA AND PHOTO SETTINGS
# ==================================================
CAMERA = "/dev/video0"
PHOTO_DIR = os.path.expanduser("~/roadbot/photos")

# Fixed example coordinates until live GPS is connected.
# These are NOT live GPS readings.
LATITUDE = 10.7735
LONGITUDE = 76.3775

# ==================================================
# SUPABASE SETTINGS
# ==================================================
SUPABASE_UPLOAD_URL = (
    "https://iglcowsagtkasxwmsqvt.supabase.co/"
    "functions/v1/robot-upload"
)
KEY_FILE = os.path.expanduser("~/.roadbot.env")
UPLOAD_RETRY_SECONDS = 10
REQUEST_TIMEOUT = 30

# ==================================================
# DETECTION AND TRACKING SETTINGS
# ==================================================
MIN_RED_AREA = 500
BOX_THICKNESS = 2
STABLE_FRAMES = 3
MATCH_DISTANCE = 140
TRACK_TIMEOUT = 10.0

# Important: this is red-colour detection, not trained AI crack detection.
LABEL = "CRACK DETECTED"

os.makedirs(PHOTO_DIR, exist_ok=True)


def load_robot_key():
    """Read ROBOT_UPLOAD_KEY from ~/.roadbot.env or environment."""
    if os.path.isfile(KEY_FILE):
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("ROBOT_UPLOAD_KEY="):
                        key = line.split("=", 1)[1].strip()
                        if (
                            len(key) >= 2
                            and key[0] == key[-1]
                            and key[0] in ("'", '"')
                        ):
                            key = key[1:-1]
                        if key:
                            return key.strip()
        except OSError as error:
            print("WARNING: Cannot read key file:", error)

    return os.environ.get("ROBOT_UPLOAD_KEY", "").strip()


ROBOT_UPLOAD_KEY = load_robot_key()

# ==================================================
# RED COLOUR RANGE (HSV)
# Detects red regions, not actual road cracks.
# ==================================================
lower1 = np.array([0, 100, 100])
upper1 = np.array([10, 255, 255])
lower2 = np.array([160, 100, 100])
upper2 = np.array([179, 255, 255])
kernel = np.ones((5, 5), np.uint8)

tracks = []
next_id = 1


def save_json_report(photo_path, timestamp):
    """Save a JSON sidecar report for a captured region."""
    report = {
        "detection": LABEL,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timestamp": timestamp,
        "photo": photo_path
    }
    report_path = os.path.splitext(photo_path)[0] + ".json"

    try:
        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=4)
        print("JSON saved:", report_path)
    except OSError as error:
        print("JSON SAVE ERROR:", error)


def upload_report(photo_path, timestamp):
    """Upload an already-saved photo. Retries never capture a new photo."""
    if not ROBOT_UPLOAD_KEY:
        print("UPLOAD ERROR: Robot key is missing.")
        return False

    try:
        with open(photo_path, "rb") as photo:
            response = requests.post(
                SUPABASE_UPLOAD_URL,
                headers={"x-robot-key": ROBOT_UPLOAD_KEY},
                data={
                    "latitude": str(LATITUDE),
                    "longitude": str(LONGITUDE),
                    "detected_at": timestamp,
                    "detection": LABEL
                },
                files={
                    "photo": (
                        os.path.basename(photo_path),
                        photo,
                        "image/jpeg"
                    )
                },
                timeout=REQUEST_TIMEOUT
            )

        if response.ok:
            print("UPLOAD SUCCESS:", photo_path)
            print("Server response:", response.text[:500])
            return True

        print("UPLOAD FAILED:", response.status_code)
        print("Server response:", response.text[:1000])
        return False

    except requests.RequestException as error:
        print("UPLOAD CONNECTION ERROR:", error)
        return False
    except OSError as error:
        print("UPLOAD FILE ERROR:", error)
        return False


# ==================================================
# OPEN CAMERA
# ==================================================
camera = cv2.VideoCapture(CAMERA)
if not camera.isOpened():
    print("ERROR: Cannot open camera:", CAMERA)
    raise SystemExit(1)

print("\n======================================")
print("          ROADBOT SYSTEM")
print("======================================")
print("Camera:", CAMERA)
print("Photos:", PHOTO_DIR)
print("Location (fixed, not live GPS):", LATITUDE, LONGITUDE)
print("Upload key:", "Loaded" if ROBOT_UPLOAD_KEY else "MISSING")
print("Mode: ONE PHOTO PER TRACKED RED REGION")
print("Detection is colour-based, not AI crack recognition.")
print("Press Q to quit.")
print("======================================\n")

try:
    while True:
        ok, frame = camera.read()

        if not ok:
            print("WARNING: Camera frame unavailable.")
            time.sleep(0.1)
            continue

        now = time.time()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask = cv2.bitwise_or(
            cv2.inRange(hsv, lower1, upper1),
            cv2.inRange(hsv, lower2, upper2)
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        detections = []
        for contour in contours:
            if cv2.contourArea(contour) < MIN_RED_AREA:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            detections.append({
                "box": (x, y, w, h),
                "center": (x + w // 2, y + h // 2)
            })

        # Keep inactive tracks briefly to avoid duplicates from flicker.
        # Keep pending uploads until the saved photo has uploaded.
        tracks = [
            track for track in tracks
            if (
                now - track["last_seen"] < TRACK_TIMEOUT
                or (
                    track["photo_path"] is not None
                    and not track["uploaded"]
                )
            )
        ]

        used_ids = set()
        new_tracks = []

        for detection in detections:
            x, y, w, h = detection["box"]
            cx, cy = detection["center"]

            best_track = None
            best_distance = MATCH_DISTANCE

            for old_track in tracks:
                if old_track["id"] in used_ids:
                    continue

                tx, ty = old_track["center"]
                distance = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5

                if distance < best_distance:
                    best_distance = distance
                    best_track = old_track

            if best_track is not None:
                track = best_track
                track["center"] = (cx, cy)
                track["last_seen"] = now
                track["count"] += 1
                used_ids.add(track["id"])
            else:
                track = {
                    "id": next_id,
                    "center": (cx, cy),
                    "last_seen": now,
                    "count": 1,
                    "photo_path": None,
                    "timestamp": None,
                    "uploaded": False,
                    "next_upload_attempt": 0
                }
                next_id += 1
                new_tracks.append(track)
                used_ids.add(track["id"])

            # Draw rectangle and label on the live preview.
            cv2.rectangle(
                frame, (x, y), (x + w, y + h),
                (0, 255, 0), BOX_THICKNESS
            )
            cv2.putText(
                frame, LABEL, (x, max(y - 8, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (0, 255, 0), 1, cv2.LINE_AA
            )

            # Capture only once after the same region is stable.
            if track["count"] >= STABLE_FRAMES and track["photo_path"] is None:
                timestamp = datetime.now(timezone.utc).isoformat()
                filename = os.path.join(
                    PHOTO_DIR,
                    "crack_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    + ".jpg"
                )

                # Save the annotated image, including box and label.
                if cv2.imwrite(filename, frame):
                    track["photo_path"] = filename
                    track["timestamp"] = timestamp
                    save_json_report(filename, timestamp)

                    print("\nNEW REGION CAPTURED")
                    print("Track ID:", track["id"])
                    print("Photo:", filename)
                    print("Location (fixed, not live GPS):", LATITUDE, LONGITUDE)
                    print("Timestamp:", timestamp)
                    print("This track will not create another photo.")
                else:
                    print("PHOTO SAVE ERROR:", filename)

        tracks.extend(new_tracks)

        # Retry uploads using the same saved photo; never recapture on retry.
        for track in tracks:
            if (
                track["photo_path"] is not None
                and not track["uploaded"]
                and now >= track["next_upload_attempt"]
            ):
                success = upload_report(track["photo_path"], track["timestamp"])

                if success:
                    track["uploaded"] = True
                    print("Track uploaded:", track["id"])
                else:
                    track["next_upload_attempt"] = (
                        time.time() + UPLOAD_RETRY_SECONDS
                    )
                    print("Will retry upload in", UPLOAD_RETRY_SECONDS, "seconds.")

        cv2.imshow("RoadBot - Crack Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        time.sleep(0.03)

except KeyboardInterrupt:
    print("\nRoadBot stopped by user.")

finally:
    camera.release()
    cv2.destroyAllWindows()
    print("Camera released.")
    print("RoadBot stopped.")
