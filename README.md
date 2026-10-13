# Varood School Working Model

This repository contains two related prototypes:

1. **ESP8266 autonomous slow car** — L298N motor driver, two DC motors, and HC-SR04 ultrasonic obstacle sensing.
2. **Raspberry Pi RoadBot** — webcam-based red-colour region detection, local photo/report saving, and upload to a Supabase Edge Function.

> **Important project status:** the camera script detects red-coloured regions, not real road cracks. The GPS wiring below is a reference for a future connection only. **Live GPS has not been implemented in the current Python script**; it still uses fixed example coordinates.

## Contents

| Project folder / file | Description |
|---|---|
| [arduino/esp8266-autonomous-car](arduino/esp8266-autonomous-car/) | ESP8266 autonomous car — Arduino sketch and obstacle-avoidance code |
| [arduino/smart-street-light](arduino/smart-street-light/) | Arduino Nano smart street-light controller |
| [raspberry_pi](raspberry_pi/) | Raspberry Pi RoadBot camera detection and upload code |

Other guides in this README:
- ESP8266 car wiring and setup
- Raspberry Pi RoadBot installation and configuration
- Upload troubleshooting and project limitations

---

## ESP8266 car

**Arduino sketch:** [esp8266_autonomous_car.ino](arduino/esp8266-autonomous-car/esp8266_autonomous_car.ino)

### Hardware

- NodeMCU ESP8266
- L298N motor driver
- Two DC motors and chassis
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

**Electrical safety:** ESP8266 GPIO pins are 3.3 V tolerant. HC-SR04 ECHO can output 5 V, so use a voltage divider or level shifter. Share ground between the ESP8266 and motor driver. Do not connect separate positive power rails together unless the power design supports it.

Open the car sketch in Arduino IDE, select **NodeMCU 1.0 (ESP-12E Module)**, upload it, and use Serial Monitor at **115200 baud**.

The ESP8266 car-control sketch and Raspberry Pi camera script are separate programs. The ESP8266 code does not process webcam images.

---

## Raspberry Pi RoadBot

### Hardware

- Raspberry Pi 3 with Raspberry Pi OS
- USB webcam compatible with Linux/V4L2 (default device: /dev/video0)
- Internet connection for Supabase uploads
- Suitable Raspberry Pi power supply
- Optional NEO-6M GPS module (wiring guide below; not yet integrated in code)

A monitor and keyboard are optional. The current camera script runs without opening a live preview window and can be started from a terminal or SSH session.

### Raspberry Pi 3 → NEO-6M GPS module (wiring guide only)

For a typical NEO-6M breakout board, connect the UART pins as follows:

| NEO-6M pin | Raspberry Pi 3 connection |
|---|---|
| VCC | Voltage supported by your exact GPS breakout board; check its label/specification |
| GND | GND — physical pin 6 |
| TX | GPIO15 / RXD, physical pin 10 |
| RX | GPIO14 / TXD, physical pin 8 (optional for basic GPS reading) |

**Important wiring notes**
- GPS TX goes to Pi RX; GPS RX goes to Pi TX. The serial data lines cross over.
- Raspberry Pi GPIO UART pins use 3.3 V logic. Do not feed a 5 V UART signal into a Pi GPIO pin. Check the GPS breakout's logic-level specification and use a suitable level shifter if needed.
- Connect the GPS and Raspberry Pi grounds together. Power the Pi off before wiring.
- Physical pin numbers differ from GPIO numbers. Double-check the pinout before connecting.
- UART setup may require enabling the serial port and disabling the serial login console in Raspberry Pi Configuration or `raspi-config`; menu names can vary by Raspberry Pi OS version.
- GPS reception is generally better with a view of the sky and may take time to get a fix.

**Current implementation status:** This is a wiring reference only. The current `red_detect.py` does **not** read `/dev/serial0`, parse GPS NMEA data, or use live GPS coordinates. It still uses `LATITUDE = 10.7735` and `LONGITUDE = 76.3775`. Connecting the module alone will not change the dashboard location; GPS support still needs to be added and tested in Python.

### What the script currently does

1. Reads webcam frames from /dev/video0.
2. Converts each frame to HSV and checks two red-colour ranges.
3. Applies morphological filtering and ignores red contours smaller than MIN_RED_AREA.
4. Tracks detections using their centre positions.
5. Waits for a region to be stable for STABLE_FRAMES.
6. Saves at most **two JPEG photos per tracked region** in ~/roadbot/photos/.
7. Writes a matching JSON report beside each saved JPEG.
8. Uploads each saved photo and its metadata to the robot-upload Supabase Edge Function.
9. Retries a failed upload using the same saved file; an upload retry does not capture another photo.
10. Stores track IDs, photo counts, and pending uploads in ~/roadbot/object_state.json so the script can restore them after restart.

The script does not show a live camera window. Stop it with **Ctrl+C** in the terminal.

### Important note about identifying the same physical object

The lightweight tracker matches red regions by centre-point distance in the camera image. It retains saved track records instead of expiring them automatically. This helps prevent repeat captures when a marking briefly disappears or the program restarts.

However, the tracker does not have a trained visual identity model. If the camera or car moves far enough, the same physical marking may appear at a very different image position and be treated as a new track. Two different red markings close together may also be matched incorrectly. The two-photo cap applies to each tracked ID; perfect real-world object identity cannot be guaranteed by this basic tracker alone.

---

## Install dependencies

Run these commands **on the Raspberry Pi Linux terminal**, not directly in Windows PowerShell:

~~~bash
sudo apt update
sudo apt install -y python3 python3-pip python3-opencv python3-numpy python3-requests v4l-utils
mkdir -p ~/roadbot/photos
~~~

Check imports:

~~~bash
python3 -c "import cv2, numpy, requests; print('OpenCV', cv2.__version__); print('Dependencies OK')"
~~~

Check the webcam:

~~~bash
ls -l /dev/video*
v4l2-ctl --list-devices
~~~

If the webcam uses a different device, edit CAMERA near the top of red_detect.py.

---

## Configure the robot upload key

The script sends multipart form data to this Edge Function:

~~~text
https://iglcowsagtkasxwmsqvt.supabase.co/functions/v1/robot-upload
~~~

The deployed function must accept the x-robot-key header and these multipart form fields:

- latitude
- longitude
- detected_at
- detection
- photo

Create the private key file on the Raspberry Pi:

~~~bash
nano ~/.roadbot.env
~~~

Add the following line, replacing the placeholder locally with the real robot upload key configured on the backend:

~~~text
ROBOT_UPLOAD_KEY=replace_with_your_real_robot_upload_key
~~~

Save with **Ctrl+O**, Enter, then **Ctrl+X**. Restrict access:

~~~bash
chmod 600 ~/.roadbot.env
~~~

Never commit this key to GitHub, put it in source code, or share it in a public chat. If the key has been exposed, rotate it in the backend. If the key is missing, local detection and photo saving can work, but uploads will fail.

---

## Quick installation and run — step by step

Follow these steps **on the Raspberry Pi 3 terminal**. If you connect remotely, use an SSH terminal connected to the Pi. Do not run Linux commands in Windows PowerShell.

### Step 1 — Install the required software

Copy and run:

~~~bash
sudo apt update
sudo apt install -y python3 python3-pip python3-opencv python3-numpy python3-requests v4l-utils
~~~

**What this does:**
- `sudo apt update` refreshes the Raspberry Pi OS package list.
- `python3` runs the Python program.
- `python3-opencv` and `python3-numpy` process webcam images.
- `python3-requests` sends photos and report data to the online server.
- `v4l-utils` helps check whether the webcam is detected.

### Step 2 — Create the folder for photos

~~~bash
mkdir -p ~/roadbot/photos
~~~

This creates the `roadbot` folder in your Pi home directory and a `photos` folder inside it. The `-p` option avoids an error if the folders already exist.

### Step 3 — Download the latest Python script

~~~bash
curl -L "https://raw.githubusercontent.com/Shanib-Muhammed/varoode-school-working-model/main/raspberry_pi/red_detect.py" -o ~/roadbot/red_detect.py
~~~

This downloads `red_detect.py` from the project's GitHub repository and saves it at `~/roadbot/red_detect.py`. Run this command again when you want to update the script.

### Step 4 — Check that the webcam is connected

~~~bash
ls -l /dev/video*
v4l2-ctl --list-devices
~~~

These commands show camera device files and detected video devices. The script expects `/dev/video0` by default. If no camera appears, check the USB connection and try another port.

### Step 5 — Set up the upload key for the website

Open the private configuration file:

~~~bash
nano ~/.roadbot.env
~~~

Add this line, replacing the example value with the real robot upload key configured for your backend:

~~~text
ROBOT_UPLOAD_KEY=replace_with_your_real_robot_upload_key
~~~

Save with **Ctrl+O**, press **Enter**, then exit with **Ctrl+X**. Protect the file:

~~~bash
chmod 600 ~/.roadbot.env
~~~

The key authorizes the robot to upload reports to the Supabase Edge Function. Do not share it or commit it to GitHub. If you have not configured the backend key, local photo detection may work but online uploads will fail.

### Step 6 — Start RoadBot

~~~bash
python3 ~/roadbot/red_detect.py
~~~

The program should try to open the webcam, detect red-coloured regions, save photos/reports, and upload them when the key and backend are configured. Read the startup messages for errors.

### Step 7 — Check saved photos

Open a second terminal, or stop the program with **Ctrl+C**, then run:

~~~bash
ls -lh ~/roadbot/photos/
~~~

This lists photos and report files saved by the script. Stop RoadBot by pressing **Ctrl+C** in the terminal where it is running.

**Important:** the current program detects red-coloured areas used as crack stand-ins; it is not a trained real-road-crack AI model. Coordinates are currently fixed in the script (`LATITUDE = 10.7735`, `LONGITUDE = 76.3775`); live GPS has not yet been implemented. Dashboard uploads also require a correctly configured upload key and a working deployed backend.

## Run RoadBot

Download the current script to the expected path:

~~~bash
mkdir -p ~/roadbot
curl -L "https://raw.githubusercontent.com/Shanib-Muhammed/varoode-school-working-model/main/raspberry_pi/red_detect.py" -o ~/roadbot/red_detect.py
~~~

Run it:

~~~bash
python3 ~/roadbot/red_detect.py
~~~

The startup messages show whether the camera opened and whether the robot upload key was loaded.

Photos and reports are saved in ~/roadbot/photos/. Persistent object state is saved in ~/roadbot/object_state.json.

Inspect saved files:

~~~bash
ls -lh ~/roadbot/photos/
~~~

When an upload fails, check the terminal output for the HTTP status code and response. The script retries the same JPEG after UPLOAD_RETRY_SECONDS; it does not take a new photo just because the upload failed.

### Updating an existing installation

Stop the running script with **Ctrl+C** first. Download the new version, then restart it:

~~~bash
curl -L "https://raw.githubusercontent.com/Shanib-Muhammed/varoode-school-working-model/main/raspberry_pi/red_detect.py" -o ~/roadbot/red_detect.py
python3 ~/roadbot/red_detect.py
~~~

The existing object_state.json preserves saved track counts. Back it up before manual changes. **Do not delete it if you want to preserve old tracking records.** If you delete it, the script starts new track IDs and may capture markings that it had previously seen.

---

## How the two-photo limit works

- A region must be seen for at least STABLE_FRAMES frames before a photo is saved.
- The first photo is saved when the region becomes stable.
- A second photo may be saved after SECOND_PHOTO_DELAY_SECONDS while the same track continues to be detected.
- A tracked ID cannot exceed MAX_PHOTOS_PER_OBJECT photos.
- Failed uploads are retried from the existing JPEG file.
- The saved state file stores each track's photo count and upload queue across restarts.

This is a per-track limit, not a guarantee that the software can always identify the same physical crack under every camera movement. If the camera view changes substantially, a marking may receive a new track ID.

---

## Configuration

Edit these values near the top of raspberry_pi/red_detect.py:

| Setting | Default | Meaning |
|---|---:|---|
| CAMERA | /dev/video0 | Webcam device |
| PHOTO_DIR | ~/roadbot/photos | JPEG and JSON report folder |
| STATE_FILE | ~/roadbot/object_state.json | Persistent tracking and upload state |
| LATITUDE | 10.7735 | Fixed example latitude, not live GPS |
| LONGITUDE | 76.3775 | Fixed example longitude, not live GPS |
| MIN_RED_AREA | 500 | Minimum contour area |
| STABLE_FRAMES | 3 | Stable frames required before capture |
| MATCH_DISTANCE | 140 | Centre-point match distance in pixels |
| MAX_PHOTOS_PER_OBJECT | 2 | Maximum photos per tracked ID |
| SECOND_PHOTO_DELAY_SECONDS | 2.0 | Minimum time before the second photo |
| UPLOAD_RETRY_SECONDS | 10 | Delay between failed upload attempts |
| REQUEST_TIMEOUT | 30 | HTTP timeout in seconds |

Red HSV ranges are [0, 100, 100]–[10, 255, 255] and [160, 100, 100]–[179, 255, 255]. Lighting, exposure, camera distance, and marking size affect detection.

---

## Troubleshooting

### Cannot open camera

Run ls -l /dev/video* and v4l2-ctl --list-devices. Set CAMERA to the correct device and ensure another program is not using the webcam.

### Robot upload key is MISSING

Check that ~/.roadbot.env contains the variable spelled exactly as ROBOT_UPLOAD_KEY. Keep the value private and run chmod 600 ~/.roadbot.env.

### Upload returns an HTTP error

Check internet access, whether robot-upload is deployed, whether the key matches the backend configuration, and whether the Edge Function expects the form fields listed above. The terminal prints the HTTP status and response body to help diagnose the failure.

### Too many or too few red detections

Adjust MIN_RED_AREA or the HSV ranges. This changes colour filtering only; it does not turn the script into an AI crack detector.

### The same marking gets a new track ID

Matching uses image-space centre distance. A large camera movement can shift the same marking too far to match. This simple tracker cannot guarantee physical object identity in every situation.

### JSON or state file cannot be written

Ensure the Pi user owns the folder and has write permission:

~~~bash
mkdir -p ~/roadbot/photos
ls -ld ~/roadbot
~~~

---

## Limitations and safety

- GPS wiring is documented, but live GPS is **not implemented** in the current script.
- Coordinates are hard-coded example values, not live GPS.
- Upload success depends on the deployed Supabase Edge Function and matching key/header/form-field contract.
- The detector finds red-coloured regions, not actual road cracks. Real crack recognition requires a suitable trained model and labelled dataset.
- The two-photo maximum is enforced per tracked ID. Large changes in camera viewpoint may cause the same physical marking to be assigned a new ID.
- Test on a stationary setup first. Do not operate a prototype on public roads without appropriate supervision and safety measures.


---

## Arduino Nano Smart Street Light Controller

The Arduino street-light prototype uses an LDR to keep the LEDs off in daylight and two HC-SR04 ultrasonic sensors to run a nine-LED sequence at night.

### Hardware required

- Arduino Nano
- 2 × HC-SR04 ultrasonic sensors
- 1 × LDR photoresistor
- 1 × 10 kΩ resistor for the LDR voltage divider
- 9 × LEDs
- 9 × 220 Ω–330 Ω resistors (one resistor per LED)
- Breadboard or prototype PCB, jumper wires, and a suitable USB/power supply

### Wiring

| Component | Signal | Arduino Nano |
|---|---|---|
| Ultrasonic sensor US1 | TRIG | D2 |
| Ultrasonic sensor US1 | ECHO | D3 |
| Ultrasonic sensor US2 | TRIG | D4 |
| Ultrasonic sensor US2 | ECHO | D5 |
| LED 1 | Anode through its resistor | D6 |
| LED 2 | Anode through its resistor | D7 |
| LED 3 | Anode through its resistor | D8 |
| LED 4 | Anode through its resistor | D9 |
| LED 5 | Anode through its resistor | D10 |
| LED 6 | Anode through its resistor | D11 |
| LED 7 | Anode through its resistor | D12 |
| LED 8 | Anode through its resistor | D13 |
| LED 9 | Anode through its resistor | A1 |
| LDR divider output | Junction between LDR and 10 kΩ resistor | A0 |
| All components | GND | Common GND |
| Both HC-SR04 sensors | VCC | 5V (for typical HC-SR04 modules) |

**LED polarity:** connect each LED's long leg (anode) to its assigned Arduino pin through an individual 220 Ω–330 Ω resistor. Connect each short leg (cathode) to GND. Do not connect LEDs directly to GPIO pins without resistors.

**LDR divider:** connect 5V → LDR → A0 junction → 10 kΩ resistor → GND. With this arrangement, the analog reading usually rises in bright light and falls in darkness. The code uses `NIGHT_THRESHOLD = 400`; adjust it to suit your room/model.

### Optional: change the LDR behavior for your exhibition

The prototype can be adjusted later without changing the wiring, provided the LDR is connected to A0 and the reading is being interpreted correctly. For your current school submission, you can keep the behavior that is already working. If you want the street lights to turn **ON in darkness and OFF in the morning/daylight**, use the normal night condition:

```cpp
bool isNight = (lightValue < NIGHT_THRESHOLD);
```

If your current prototype instead turns LEDs **ON in bright morning light and OFF in darkness**, you can try reversing the comparison:

```cpp
bool isNight = (lightValue > NIGHT_THRESHOLD);
```

Choose the condition that matches your actual LDR wiring and readings. With the documented wiring above, the first condition is normally correct; if the behavior is reversed, check the voltage-divider wiring and print `lightValue` to the Serial Monitor before changing the condition. To adjust when it switches between day and night, change `NIGHT_THRESHOLD` (currently `400`) and test—for example, try `500`, then tune it based on the readings. After editing the sketch, click **Verify** and **Upload** in Arduino IDE. These are optional settings, so you can leave the working prototype unchanged for the morning demonstration and change them later if needed.

### Upload the sketch

1. Install and open the Arduino IDE on your computer.
2. Connect the Arduino Nano with a USB data cable.
3. Open [SmartStreetLightController.ino](arduino/smart-street-light/SmartStreetLightController.ino).
4. In **Tools → Board**, select **Arduino Nano**.
5. In **Tools → Processor**, select the processor matching your Nano. Many classic Nano clones use **ATmega328P (Old Bootloader)**; if upload fails, try the other ATmega328P option.
6. In **Tools → Port**, select the port for your Nano.
7. Click **Verify**, then **Upload**.
8. Optional: open **Tools → Serial Monitor** and select **9600 baud** to see sensor-event messages.

### How it works

- **Daylight:** all LEDs are turned off based on the LDR reading.
- **At night, US1 detects an object within 5 cm:** LEDs 1 through 9 turn on one at a time.
- **At night, US2 detects an object within 5 cm after the US1 sequence:** LEDs 1 through 9 turn off one at a time.
- **At night, US2 detects an object within 5 cm first:** LEDs 9 through 1 turn on one at a time.
- **At night, US1 detects an object within 5 cm after the reverse sequence:** LEDs 9 through 1 turn off one at a time.
- A sensor is re-armed after the object moves to at least 8 cm away. This helps avoid repeatedly triggering while an object remains very close.
- The LED step delay is 200 ms per LED.

### Adjustments and troubleshooting

The main settings are near the top of the sketch:

- `NIGHT_THRESHOLD = 400`: adjust for your LDR and room brightness.
- `DETECT_DISTANCE_CM = 5`: detection threshold in centimetres.
- `RELEASE_DISTANCE_CM = 8`: distance required to re-arm the sensor.
- `LED_STEP_MS = 200`: time between LED steps, in milliseconds.

If only some LEDs work, first upload a simple LED test sketch and check each LED, its individual resistor, polarity, and pin connection. Verify that LED 9 is connected to A1 and that all grounds are connected together. D13 and A1 are valid output pins on a classic Arduino Nano. The sensor threshold cannot explain why particular LEDs fail in an independent LED test.

**Safety and limitations:** test the model on a stable work surface. HC-SR04 readings can be less reliable at very short distances; if 5 cm is inconsistent, try 6–8 cm. The LDR threshold depends on the actual divider wiring and ambient light.