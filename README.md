# Varood School Working Model

This repository contains two related but separate prototypes:

1. **ESP8266 slow car** — drives two DC motors through an L298N and uses an HC-SR04 ultrasonic sensor to stop near an obstacle.
2. **Raspberry Pi RoadBot camera prototype** — detects red-coloured regions, saves one photo per tracked region, writes a JSON report, and uploads the saved photo and coordinates to a Supabase Edge Function.

> **Important limitation:** the current Raspberry Pi program detects the colour red. It does **not** recognise real road cracks using AI. The coordinates are hard-coded example coordinates until a live GPS receiver is connected. Do not present these as live GPS readings.

---

## Contents

- [ESP8266 car prototype](#esp8266-car-prototype)
- [Raspberry Pi RoadBot](#raspberry-pi-roadbot)
- [Hardware needed for RoadBot](#hardware-needed-for-roadbot)
- [Install Raspberry Pi dependencies](#install-raspberry-pi-dependencies)
- [Camera check](#camera-check)
- [Configure the Supabase robot key](#configure-the-supabase-robot-key)
- [Copy the script from GitHub to the Pi](#copy-the-script-from-github-to-the-pi)
- [Run RoadBot](#run-roadbot)
- [What the program does](#what-the-program-does)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Safety and limitations](#safety-and-limitations)

---

## ESP8266 car prototype

### Hardware

- NodeMCU ESP8266
- L298N motor driver
- 2 DC motors and chassis
- HC-SR04 ultrasonic sensor
- Suitable battery and regulated power supply

### Pin connections

**L298N → ESP8266**

| L298N pin | ESP8266 pin |
|---|---|
| ENA | D3 |
| IN1 | D1 |
| IN2 | D2 |
| ENB | D4 |
| IN3 | D5 |
| IN4 | D6 |

**HC-SR04 → ESP8266**

| HC-SR04 pin | Connection |
|---|---|
| TRIG | D7 |
| ECHO | D8 through a voltage divider or level shifter |
| GND | GND |
| VCC | Suitable 5 V supply |

> **Electrical warning:** HC-SR04 ECHO can output 5 V, but ESP8266 GPIO is 3.3 V tolerant. Use a voltage divider or level shifter. Share ground between the ESP8266 and motor driver. Do not connect separate positive power rails together unless the power design specifically supports it.

The Arduino sketch is `esp8266_autonomous_car.ino`. Open it in Arduino IDE, select **NodeMCU 1.0 (ESP-12E Module)**, upload it, and use Serial Monitor at **115200 baud**.

---

## Raspberry Pi RoadBot

### Hardware needed for RoadBot

- Raspberry Pi 3 with Raspberry Pi OS
- USB webcam compatible with Linux/V4L2 (the script defaults to `/dev/video0`)
- Internet connection for Supabase upload
- Power supply suitable for the Pi
- Optional future addition: a supported GPS module for live coordinates

A monitor, keyboard, and mouse are optional if you connect to the Pi over SSH.

### What it does

1. Opens the webcam at `/dev/video0`.
2. Converts each frame from BGR to HSV colour space.
3. Checks two HSV ranges to detect red pixels.
4. Removes small noise and ignores contours smaller than `MIN_RED_AREA`.
5. Tracks each detected region between frames using its centre point.
6. Waits until a region is seen for at least `STABLE_FRAMES` frames.
7. Saves **one annotated JPEG per tracked region** in `~/roadbot/photos/`.
8. Writes a matching JSON report beside the image.
9. Uploads the already-saved photo, detection label, timestamp, and configured coordinates to the Supabase Edge Function.
10. If upload fails, retries the **same saved photo** after the configured delay instead of taking a new photo.
11. Shows a live preview with a green rectangle and the label `CRACK DETECTED`. Press **Q** in the preview window to exit, or press **Ctrl+C** in the terminal.

The label is only a project label; the current algorithm is colour detection, not a trained crack classifier.

---

## Install Raspberry Pi dependencies

Run these commands **on the Raspberry Pi terminal**, not directly in Windows PowerShell. If you use PowerShell on your PC, first connect to the Pi with SSH as described below.

Update the package list:

```bash
sudo apt update
```

Install Python, pip, OpenCV, NumPy, and camera utilities:

```bash
sudo apt install -y python3 python3-pip python3-opencv python3-numpy python3-requests v4l-utils
```

Check that the required modules import correctly:

```bash
python3 -c "import cv2, numpy, requests; print('OpenCV', cv2.__version__); print('Dependencies OK')"
```

Create the project folders:

```bash
mkdir -p ~/roadbot/photos
```

---

## Camera check

List video devices:

```bash
ls -l /dev/video*
```

List cameras known to V4L2:

```bash
v4l2-ctl --list-devices
```

If the camera is not `/dev/video0`, edit `CAMERA` near the top of `red_detect.py` to use the correct device, for example `/dev/video2`.

Make sure no other program is already using the webcam.

---

## Configure the Supabase robot key

The script sends uploads to this Supabase Edge Function:

```text
https://iglcowsagtkasxwmsqvt.supabase.co/functions/v1/robot-upload
```

The server must already have this function deployed and configured to accept the `x-robot-key` header and the form fields used by the script.

Create the private key file on the Raspberry Pi:

```bash
nano ~/.roadbot.env
```

Add this line, replacing the placeholder with the real robot upload key supplied by your project/backend administrator:

```text
ROBOT_UPLOAD_KEY=replace_with_your_real_robot_upload_key
```

Save in nano: press **Ctrl+O**, press **Enter**, then **Ctrl+X**.

Restrict access to the file:

```bash
chmod 600 ~/.roadbot.env
```

Do not commit this key to GitHub, paste it into source code, or share it publicly. The Python script reads the key from `~/.roadbot.env`. If it is missing, image detection and local saving can still work, but uploads will fail until the key is configured.

---

## Copy the script from GitHub to the Pi

### Option A — download the script directly

On the Raspberry Pi, run:

```bash
mkdir -p ~/roadbot
curl -L "https://raw.githubusercontent.com/Shanib-Muhammed/varoode-school-working-model/main/raspberry_pi/red_detect.py" -o ~/roadbot/red_detect.py
```

Check that the file exists:

```bash
ls -l ~/roadbot/red_detect.py
```

### Option B — clone the whole repository

If Git is installed, you can clone the repository:

```bash
sudo apt install -y git
git clone https://github.com/Shanib-Muhammed/varoode-school-working-model.git
```

The script will be at:

```text
varoode-school-working-model/raspberry_pi/red_detect.py
```

To run it from the repository folder:

```bash
python3 varoode-school-working-model/raspberry_pi/red_detect.py
```

If you specifically want the script at `~/roadbot/red_detect.py`, use Option A or copy it from the cloned repository:

```bash
mkdir -p ~/roadbot
cp varoode-school-working-model/raspberry_pi/red_detect.py ~/roadbot/red_detect.py
```

---

## Run RoadBot

Run the script on the Raspberry Pi:

```bash
python3 ~/roadbot/red_detect.py
```

The startup output should show the camera path, photo directory, configured coordinates, and whether the robot upload key was loaded. If the camera cannot open, check the device path and camera connection.

When a red region stays visible for the required number of frames, the program prints the track ID, saved photo path, coordinates, and timestamp. It then attempts to upload the photo.

### View saved photos and JSON reports

```bash
ls -lh ~/roadbot/photos/
```

Each successful local capture should have a JPEG and a matching JSON file, for example:

```text
crack_20261011_123456_123456.jpg
crack_20261011_123456_123456.json
```

The JSON report contains the detection label, configured latitude and longitude, timestamp, and local photo path.

### Stop the program

- Press **Q** while the live preview window is selected.
- Or press **Ctrl+C** in the terminal.

---

## If you use Windows PowerShell to connect to the Raspberry Pi

PowerShell is running on your Windows PC; commands such as `sudo apt`, `ls /dev/video*`, and `python3 ~/roadbot/red_detect.py` are intended to run **after you log in to the Raspberry Pi's Linux shell**.

From PowerShell, connect using the Pi's actual username and hostname or IP address:

```powershell
ssh <username>@<raspberry-pi-hostname-or-ip>
```

For example, if the Pi's username is `raspberrypi` and its reachable hostname is `raspberrypi.local`:

```powershell
ssh raspberrypi@raspberrypi.local
```

If that hostname cannot be resolved, use the Pi's IP address or fix hostname/network discovery first. After SSH connects, run the Linux commands in the sections above in the remote shell. The path `~/roadbot/red_detect.py` refers to the home directory of the Linux user logged in on the Pi, not a folder on Windows.

---

## Configuration

These constants are near the top of `red_detect.py`:

| Setting | Default | Meaning |
|---|---:|---|
| `CAMERA` | `/dev/video0` | Linux camera device |
| `PHOTO_DIR` | `~/roadbot/photos` | Where JPEGs and JSON reports are saved |
| `LATITUDE` | `10.7735` | Fixed example latitude; not live GPS |
| `LONGITUDE` | `76.3775` | Fixed example longitude; not live GPS |
| `MIN_RED_AREA` | `500` | Ignore smaller red contours |
| `STABLE_FRAMES` | `3` | Frames required before capture |
| `MATCH_DISTANCE` | `140` | Maximum centre-point distance for track matching, in pixels |
| `TRACK_TIMEOUT` | `10.0` | Seconds a missing region is retained to reduce duplicate captures |
| `UPLOAD_RETRY_SECONDS` | `10` | Wait between failed upload attempts |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |

The two red HSV ranges are `[0, 100, 100]–[10, 255, 255]` and `[160, 100, 100]–[179, 255, 255]`. Lighting, camera exposure, distance, and object size affect results.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'cv2'`

Run:

```bash
sudo apt install -y python3-opencv
```

### `No module named 'requests'`

Run:

```bash
sudo apt install -y python3-requests
```

### `Cannot open camera: /dev/video0`

Run `ls -l /dev/video*` and `v4l2-ctl --list-devices`. Set `CAMERA` to the correct device and check the USB connection.

### `Robot key is missing`

Check the file and variable spelling:

```bash
cat ~/.roadbot.env
chmod 600 ~/.roadbot.env
```

Keep the key private. If it has been exposed publicly, rotate it in the backend.

### Upload returns an HTTP error

Check the internet connection, that the Supabase Edge Function is deployed, that the key matches the backend configuration, and that the function expects the form field names `latitude`, `longitude`, `detected_at`, `detection`, and `photo`.

### Too many or too few detections

Adjust `MIN_RED_AREA` and the HSV ranges. This changes red-colour filtering only; it does not make the program an AI crack detector.

### Same region is captured again later

Tracking is based on the detected region's centre point. If the camera moves, a region disappears longer than `TRACK_TIMEOUT`, or detections shift significantly, the same physical object may be treated as a new region. This lightweight tracker cannot guarantee perfect physical crack identity.

---

## Safety and limitations

- The script uses **fixed example coordinates**, not a live GPS receiver.
- A successful upload depends on the Supabase Edge Function and its authentication configuration.
- Detection is based on **red colour**, not actual road-crack features. A trained model and labelled crack-image dataset are needed for real crack recognition.
- The camera preview requires a graphical desktop session. If running over SSH without a display, `cv2.imshow` may fail; run it on the Pi desktop or configure a headless preview approach.
- Test on a stationary setup before mounting the camera on a moving vehicle.
- Do not operate a prototype on public roads without appropriate supervision and safety measures.
