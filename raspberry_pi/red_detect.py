import cv2
import numpy as np
import os
import time
import json
import requests
from datetime import datetime, timezone

# ==================================================
# CAMERA, STORAGE, AND LOCATION
# ==================================================
CAMERA = "/dev/video0"
PHOTO_DIR = os.path.expanduser("~/roadbot/photos")
STATE_FILE = os.path.expanduser("~/roadbot/object_state.json")
os.makedirs(PHOTO_DIR, exist_ok=True)

# Fixed example coordinates; these are NOT live GPS readings.
LATITUDE = 10.7735
LONGITUDE = 76.3775

# ==================================================
# SUPABASE UPLOAD
# ==================================================
SUPABASE_UPLOAD_URL = (
    "https://iglcowsagtkasxwmsqvt.supabase.co/"
    "functions/v1/robot-upload"
)
KEY_FILE = os.path.expanduser("~/.roadbot.env")
UPLOAD_RETRY_SECONDS = 10
REQUEST_TIMEOUT = 30

# ==================================================
# RED DETECTION AND TRACKING
# ==================================================
MIN_RED_AREA = 500
BOX_THICKNESS = 1
STABLE_FRAMES = 3
MATCH_DISTANCE = 140

# Maximum number of JPEGs saved for a tracked object.
MAX_PHOTOS_PER_OBJECT = 2
# Earliest time allowed between photo 1 and photo 2 for one track.
SECOND_PHOTO_DELAY_SECONDS = 2.0

LABEL = "CRACK DETECTED"

lower1 = np.array([0, 100, 100])
upper1 = np.array([10, 255, 255])
lower2 = np.array([160, 100, 100])
upper2 = np.array([179, 255, 255])
kernel = np.ones((5, 5), np.uint8)

tracks = []
next_id = 1


def load_robot_key():
    """Read the secret robot key from ~/.roadbot.env or the environment."""
    if os.path.isfile(KEY_FILE):
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("ROBOT_UPLOAD_KEY="):
                        key = line.split("=", 1)[1].strip()
                        if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
                            key = key[1:-1]
                        if key:
                            return key.strip()
        except OSError as error:
            print("WARNING: Cannot read robot key:", error)

    return os.environ.get("ROBOT_UPLOAD_KEY", "").strip()


ROBOT_UPLOAD_KEY = load_robot_key()


def save_state():
    """Persist track IDs and photo counts across program restarts."""
    temp_path = STATE_FILE + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump({"next_id": next_id, "tracks": tracks}, file, indent=2)
    os.replace(temp_path, STATE_FILE)


def load_state():
    global tracks, next_id

    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            state = json.load(file)

        tracks = state.get("tracks", [])
        next_id = state.get("next_id", 1)

        for track in tracks:
            track["matched"] = False
            track["stable_frames"] = 0
            # JSON restores saved fields; ensure newer fields have defaults.
            track.setdefault("photo_count", 0)
            track.setdefault("last_photo_time", 0.0)
            track.setdefault("uploads", [])

        print("Loaded saved object records:", len(tracks))
    except (OSError, json.JSONDecodeError, TypeError) as error:
        print("WARNING: Could not load saved tracking state:", error)


def save_json_report(photo_path, timestamp, object_id, photo_number):
    report = {
        "detection": LABEL,
        "object_id": object_id,
        "photo_number": photo_number,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timestamp": timestamp,
        "photo": photo_path
    }
    report_path = os.path.splitext(photo_path)[0] + ".json"
    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)


def upload_report(photo_path, timestamp):
    """Upload an already-saved image. Retries never capture another photo."""
    if not ROBOT_UPLOAD_KEY:
        print("UPLOAD ERROR: Robot key is missing in ~/.roadbot.env")
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

        print("UPLOAD FAILED:", response.status_code, response.text[:1000])
        return False

    except requests.RequestException as error:
        print("UPLOAD CONNECTION ERROR:", error)
        return False
    except OSError as error:
        print("UPLOAD FILE ERROR:", error)
        return False


def detect_red(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.bitwise_or(
        cv2.inRange(hsv, lower1, upper1),
        cv2.inRange(hsv, lower2, upper2)
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

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

    return detections


def capture_photo(frame, track, detection):
    """Save and queue one photo, respecting the per-track two-photo limit."""
    if track["photo_count"] >= MAX_PHOTOS_PER_OBJECT:
        return

    photo_number = track["photo_count"] + 1
    timestamp = datetime.now(timezone.utc).isoformat()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    photo_path = os.path.join(
        PHOTO_DIR,
        f"crack_{track['id']}_photo{photo_number}_{stamp}.jpg"
    )

    output = frame.copy()
    x, y, w, h = detection["box"]
    cv2.rectangle(
        output, (x, y), (x + w, y + h), (0, 255, 0), BOX_THICKNESS
    )
    cv2.putText(
        output, LABEL, (x, max(y - 8, 20)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
        cv2.LINE_AA
    )

    if not cv2.imwrite(photo_path, output):
        print("PHOTO SAVE ERROR:", photo_path)
        return

    track["photo_count"] = photo_number
    track["last_photo_time"] = time.time()
    track.setdefault("uploads", []).append({
        "path": photo_path,
        "timestamp": timestamp,
        "uploaded": False,
        "next_attempt": 0.0
    })

    save_json_report(photo_path, timestamp, track["id"], photo_number)
    save_state()

    print(
        f"OBJECT {track['id']}: saved photo "
        f"{photo_number}/{MAX_PHOTOS_PER_OBJECT}: {photo_path}"
    )


def process_upload_queue():
    """Upload pending saved images and retry failed uploads without recapture."""
    now = time.time()

    for track in tracks:
        for item in track.get("uploads", []):
            if item.get("uploaded", False):
                continue
            if now < item.get("next_attempt", 0.0):
                continue

            if upload_report(item["path"], item["timestamp"]):
                item["uploaded"] = True
            else:
                item["next_attempt"] = time.time() + UPLOAD_RETRY_SECONDS

            save_state()


def main():
    global next_id

    load_state()
    camera = cv2.VideoCapture(CAMERA)

    if not camera.isOpened():
        print("ERROR: Cannot open camera:", CAMERA)
        return

    print("\n======================================")
    print("       ROADBOT RED DETECTION")
    print("======================================")
    print("Camera:", CAMERA)
    print("Photos:", PHOTO_DIR)
    print("Location (fixed, not live GPS):", LATITUDE, LONGITUDE)
    print("Robot upload key:", "Loaded" if ROBOT_UPLOAD_KEY else "MISSING")
    print("Maximum photos per tracked object:", MAX_PHOTOS_PER_OBJECT)
    print("Camera preview is disabled; detection runs in the background.")
    print("Stop with Ctrl+C.")
    print("======================================\n")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("WARNING: Camera frame unavailable.")
                process_upload_queue()
                time.sleep(0.2)
                continue

            detections = detect_red(frame)

            for track in tracks:
                track["matched"] = False

            for detection in detections:
                cx, cy = detection["center"]
                best_track = None
                best_distance = MATCH_DISTANCE

                # Match one current detection to one existing record.
                for track in tracks:
                    if track["matched"]:
                        continue

                    tx, ty = track["center"]
                    distance = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
                    if distance < best_distance:
                        best_distance = distance
                        best_track = track

                if best_track is None:
                    best_track = {
                        "id": next_id,
                        "center": [cx, cy],
                        "stable_frames": 0,
                        "photo_count": 0,
                        "last_photo_time": 0.0,
                        "matched": False,
                        "uploads": []
                    }
                    tracks.append(best_track)
                    next_id += 1
                    print("New red-region track:", best_track["id"])

                best_track["center"] = [cx, cy]
                best_track["matched"] = True
                best_track["stable_frames"] = best_track.get("stable_frames", 0) + 1

                # First photo after stable detection; second only after a delay.
                if best_track["stable_frames"] >= STABLE_FRAMES:
                    photo_count = best_track.get("photo_count", 0)
                    delay_passed = (
                        time.time() - best_track.get("last_photo_time", 0.0)
                        >= SECOND_PHOTO_DELAY_SECONDS
                    )

                    if photo_count == 0 or (
                        photo_count < MAX_PHOTOS_PER_OBJECT and delay_passed
                    ):
                        capture_photo(frame, best_track, detection)

            # Never expire saved tracks automatically: this avoids forgetting
            # a previously captured marking when it briefly leaves the frame.
            save_state()
            process_upload_queue()
            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\nRoadBot stopped by user.")

    finally:
        save_state()
        camera.release()
        print("Camera released. Tracking state saved.")


if __name__ == "__main__":
    main()
