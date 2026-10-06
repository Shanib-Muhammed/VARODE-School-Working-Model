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
