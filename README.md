# 🚗 ESP8266 Autonomous Slow Car

A simple autonomous car prototype using an **ESP8266 NodeMCU**, **L298N motor driver**, **2 DC motors**, and an **HC-SR04 ultrasonic sensor**.

The car moves forward slowly and continuously checks the distance in front of it. When an obstacle gets closer, the car gradually reduces its speed. When the obstacle reaches the configured stop distance, the car stops.

## Components
- NodeMCU ESP8266
- L298N Motor Driver
- 2 × DC motors
- HC-SR04 ultrasonic sensor
- Suitable battery/power supply
- Robot chassis and wheels

## Features
- Slow forward movement
- Continuous front-distance measurement
- Automatic speed reduction near obstacles
- Automatic stop at the configured distance
- Serial Monitor status output

## Pin Connections

### L298N → ESP8266

| L298N | ESP8266 |
|---|---|
| ENA | D3 |
| IN1 | D1 |
| IN2 | D2 |
| ENB | D4 |
| IN3 | D5 |
| IN4 | D6 |

### HC-SR04 → ESP8266

| HC-SR04 | ESP8266 |
|---|---|
| TRIG | D7 |
| ECHO | D8 |
| GND | GND |
| VCC | 5V supply |

> ⚠️ **Important:** HC-SR04 ECHO can output 5V, while ESP8266 GPIO uses 3.3V logic. Use a voltage divider/level shifter on ECHO before connecting it to the ESP8266.

## Movement Logic

Current settings:

```cpp
const int SAFE_DISTANCE = 15;
const int STOP_DISTANCE = 8;
const int MAX_SPEED = 70;
const int MIN_SPEED = 25;
```

- **More than 15 cm:** car moves forward at MAX_SPEED.
- **15 cm to 8 cm:** car gradually slows down.
- **8 cm or less:** car stops.
- **Invalid ultrasonic reading:** car stops for safety.

## Serial Monitor

Use **115200 baud**.

## Arduino IDE

- **Board:** NodeMCU 1.0 (ESP-12E Module)
- **Serial Monitor:** 115200 baud
- **Sketch:** `esp8266_autonomous_car.ino`

## Power and Ground

ESP8266 and L298N must share a common ground:

```
ESP8266 GND ───── L298N GND
Battery − ─────── L298N GND
```

Do **not** connect different positive power supplies together.

## Project Status

This is the first movement prototype of the **Varood School working model**. Future versions can add Raspberry Pi vision, road-crack detection, GPS, image capture, and a web dashboard.

## License

Educational and robotics experimentation project.


---

# Raspberry Pi Road-Colour Detection Prototype

This is a separate Raspberry Pi 3 prototype for testing camera-based red-colour detection. It does not replace the ESP8266 car-movement prototype above.

## Hardware and software

- Raspberry Pi 3
- Logitech C925e USB webcam (or another compatible USB webcam)
- Python 3
- OpenCV (`cv2`)
- NumPy

> **Current scope:** This prototype detects red-coloured regions. It does not yet identify real road cracks. Road cracks are not normally red; a trained crack-detection model or another image-processing approach will be needed for real road-crack recognition.

## Features

- Continuously reads webcam frames in the background.
- Does not open a live preview window.
- Converts frames from BGR to HSV colour space.
- Uses two HSV ranges because red wraps around the hue scale.
- Filters small noise and finds red-region contours.
- Draws a green bounding rectangle and a `RED DETECTED` label around sufficiently large red regions.
- Saves one annotated photo when red first appears, rather than saving every video frame.
- Saves photos in `~/roadbot/photos/`.
- Stops with `Ctrl+C`.

## Check the camera

List video devices:

```bash
ls /dev/video*
```

Install camera utilities and list camera names/devices:

```bash
sudo apt install v4l-utils -y
v4l2-ctl --list-devices
```

The Logitech C925e was detected during development; `/dev/video0` successfully returned a frame. Device numbers may differ on other systems.

## Install dependencies

```bash
sudo apt update
sudo apt install python3-opencv python3-numpy
```

Check OpenCV:

```bash
python3 -c "import cv2; print(cv2.__version__)"
```

## Run the detector

Create the output folder:

```bash
mkdir -p ~/roadbot/photos
```

Copy `raspberry_pi/red_detect.py` from this repository to `~/roadbot/red_detect.py`, then run:

```bash
python3 ~/roadbot/red_detect.py
```

Show a red paper or red tape to the webcam. When red is detected, the terminal prints the saved image path. To list saved photos:

```bash
ls -lh ~/roadbot/photos/
```

Press `Ctrl+C` to stop the detector.

## Configuration

- Camera device: `/dev/video0`
- Minimum contour area: `500` pixels
- HSV red ranges: `[0, 100, 100]–[10, 255, 255]` and `[160, 100, 100]–[179, 255, 255]`
- Output folder: `~/roadbot/photos/`

Lighting, camera settings, distance, and object size affect detection. Adjust `MIN_RED_AREA` and the HSV limits if false detections occur or red objects are missed.

## Current limitations and planned work

- NEO-6M GPS integration is not included in this script yet.
- Automatic website upload is not included yet.
- GitHub Pages is a static website and cannot by itself securely receive uploads or store uploaded photos. A backend/storage service (for example, Supabase) is needed for photo and GPS reports.
- Red-colour detection is a test proxy, not confirmed road-crack detection.
- Startup-on-boot configuration has not been added yet.
