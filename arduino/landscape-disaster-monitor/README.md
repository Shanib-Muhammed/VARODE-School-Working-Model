# Varode Landscape Disaster Monitor (Arduino UNO)

A school science-exhibition prototype that demonstrates how soil moisture and rain readings can be used to show warning messages on a 0.96-inch OLED screen.

> **Educational model only:** This is not a certified landslide prediction or public-safety system. The percentages are scaled sensor readings, and the 50% thresholds are demonstration settings. Do not use this prototype to make real-world evacuation or safety decisions.

## Features

- Reads an analog soil-moisture sensor on Arduino UNO pin A0.
- Reads an analog rain sensor on pin A1.
- Averages 10 readings from each sensor to reduce small fluctuations.
- Converts raw readings into approximate 0–100% values.
- Displays status and sensor percentages on a 128×64 SSD1306 OLED.
- Displays an alert when either sensor reaches 50%:
  - Both soil and rain at/above 50%: **LANDSLIDE WARNING!**
  - Soil at/above 50% only: **SOIL WET WARNING!**
  - Rain at/above 50% only: **HEAVY RAIN WARNING!**
  - Neither at/above 50%: **SYSTEM NORMAL**
- Prints raw readings, percentages, and alert state to Serial Monitor.

The water-level sensor and MPU6050/tilt sensor are not used in this version.

## Components

- Arduino UNO (or compatible 5 V UNO board)
- 0.96-inch 128×64 SSD1306 I²C-compatible OLED display
- Analog soil-moisture sensor/module
- Analog rain sensor/module
- Breadboard and jumper wires
- USB cable for programming and power
- Optional separate regulated supply if required by your sensor modules

Check the labels and voltage requirements of your exact modules before connecting them.

## Wiring

### OLED display (software I²C in this sketch)

This sketch deliberately uses digital pins D2 and D3 for software I²C.

| OLED pin | Arduino UNO |
|---|---|
| SDA | D2 |
| SCL | D3 |
| GND | GND |
| VCC | Supply supported by your OLED module (many breakout boards accept 3.3–5 V; check yours) |

**Important:** The constructor in the sketch is configured as SCL = D3 and SDA = D2. Do not connect the OLED to A4/A5 unless you also change the code to use hardware I²C.

### Analog sensors

| Sensor/module pin | Arduino UNO |
|---|---|
| Soil sensor AO / AOUT | A0 |
| Soil sensor GND | GND |
| Soil sensor VCC | Module-rated supply |
| Rain sensor AO / AOUT | A1 |
| Rain sensor GND | GND |
| Rain sensor VCC | Module-rated supply |

- Connect **AO/AOUT**, not DO, for the analog percentage calculation.
- Connect all module grounds to Arduino GND.
- If a sensor board has both AO and DO, DO is a digital threshold output and is not used by this sketch.
- Avoid allowing water to contact the Arduino, USB connection, or exposed wiring. Test the rain sensor carefully and keep electronics dry.

## Software requirements

- Arduino IDE 2.x (Arduino IDE 1.8.x is also suitable)
- **U8g2** library by olikraus

### Install U8g2

1. Open Arduino IDE.
2. Choose **Sketch → Include Library → Manage Libraries** (in IDE 2.x, open Library Manager).
3. Search for **U8g2**.
4. Install **U8g2 by olikraus**.
5. Open `landscape_disaster_monitor.ino`.

The `Wire.h` library is included with the Arduino AVR board package; no separate installation is normally required.

## Upload the sketch

1. Connect the Arduino UNO to the computer with a USB data cable.
2. Open `landscape_disaster_monitor.ino` in Arduino IDE.
3. Under **Tools → Board**, select **Arduino AVR Boards → Arduino Uno** (or the matching board).
4. Under **Tools → Port**, select the port for your Arduino.
5. Click **Verify** (checkmark) to compile.
6. Click **Upload** (right arrow).
7. Open **Tools → Serial Monitor** and select **115200 baud** to see readings and status messages.

If compilation reports that `U8g2lib.h` is missing, install the U8g2 library and compile again.

## How the system works

1. The Arduino samples the soil sensor and rain sensor 10 times each.
2. It averages the samples.
3. It maps each raw value to an approximate percentage using the calibration values in the sketch.
4. If either percentage is 50% or higher, the OLED shows a warning. If both reach the threshold, the combined landslide warning takes priority.
5. The OLED refreshes and the Serial Monitor prints the current readings approximately every 300 ms, plus the sensor sampling time.

The OLED is monochrome; warning states are communicated with text, not red/green colours.

## Calibrate the sensor values

The starting values in the sketch are examples and **may not match your sensors**:

```cpp
const int SOIL_DRY = 800;
const int SOIL_WET = 350;

const int RAIN_DRY = 900;
const int RAIN_WET = 300;
```

Calibration procedure:

1. Upload the sketch and open Serial Monitor at **115200 baud**.
2. Record `Soil Raw` while the soil sensor is in the driest condition you want to represent.
3. Record `Soil Raw` in the wet condition you want to represent.
4. Put those readings into `SOIL_DRY` and `SOIL_WET`, respectively.
5. Repeat for the rain sensor and update `RAIN_DRY` and `RAIN_WET`.
6. Upload again and test dry, damp, and wet conditions.

The mapping assumes the raw reading moves from the dry value toward the wet value. If your module behaves in the opposite direction, use the actual measured dry and wet endpoints in the corresponding constants and verify the displayed percentage changes in the expected direction. Keep dry and wet constants different.

## Change the warning threshold

The default warning thresholds are 50%:

```cpp
const int SOIL_WARNING_THRESHOLD = 50;
const int RAIN_WARNING_THRESHOLD = 50;
```

Change these values if you want to demonstrate different alert points. These are simple exhibition thresholds, not scientifically validated landslide thresholds.

## Troubleshooting

### OLED remains blank

- Confirm VCC and GND.
- Check SDA → D2 and SCL → D3 exactly as listed.
- Confirm the display is an SSD1306 128×64 model compatible with the constructor.
- Ensure the U8g2 library is installed.
- Check for loose jumper wires and try a known-good display module.

### Compile error: `U8g2lib.h: No such file or directory`

Install **U8g2 by olikraus** using Library Manager, then restart compilation.

### Percentages stay at 0% or 100%

- Check that AO/AOUT is connected to the correct analog input (A0 for soil, A1 for rain).
- Read the raw values in Serial Monitor.
- Calibrate the dry and wet constants using actual readings.
- Confirm sensor power and common ground.

### Sensor percentages seem reversed

Some sensor boards produce lower analog readings when wet; others may behave differently. Record dry and wet raw readings and assign those measurements to the correct constants. The code maps `dryValue` to 0% and `wetValue` to 100%.

### Warning appears too often

Calibrate the sensor endpoints first. You can then raise the warning threshold, but remember that this only changes the demonstration behaviour.

### First letters or text are clipped

Keep the OLED wiring and display resolution correct. This sketch calculates the horizontal text position using the selected font width. A different display or font may need layout adjustments.

## Project structure

```text
arduino/
└── landscape-disaster-monitor/
    ├── landscape_disaster_monitor.ino
    └── README.md
```

## Limitations

- No water-level sensor is read by this sketch.
- No MPU6050 or tilt measurement is used.
- Sensor percentages are approximate and depend on calibration, sensor design, power, and environmental conditions.
- Soil moisture and rain alone cannot reliably predict a landslide. A real monitoring system needs appropriate validated sensors, site-specific analysis, robust installation, and expert oversight.

## Repository

[Varode School Working Model — Arduino projects](https://github.com/Shanib-Muhammed/VARODE-School-Working-Model/tree/main/arduino)
