#include <Wire.h>
#include <U8g2lib.h>
#include <Servo.h>
#include <math.h>

// ==================================================
// VARODE LANDSCAPE DISASTER MANAGEMENT SYSTEM
// Arduino UNO + OLED + Soil + Rain + MPU6050
// HC-SR04 + Servo Barrier + Buzzer
// ==================================================

// OLED SSD1306 128x64; software I2C: SCL D3, SDA D2
U8G2_SSD1306_128X64_NONAME_1_SW_I2C u8g2(
  U8G2_R0, 3, 2, U8X8_PIN_NONE
);

// Pins
const int SOIL_PIN = A0;
const int RAIN_PIN = A1;
const int BUZZER_PIN = 8;
const int TRIG_PIN = 6;
const int ECHO_PIN = 7;
const int SERVO_PIN = 9;

Servo barrierServo;

// Servo angles
const int BARRIER_OPEN_ANGLE = 0;
const int BARRIER_CLOSED_ANGLE = 90;

// Vehicle detection and timer
const float VEHICLE_DISTANCE_CM = 5.0;
const unsigned long CLEAR_DELAY_MS = 3000;

// Sensor calibration
const int SOIL_DRY = 800;
const int SOIL_WET = 350;
const int RAIN_DRY = 900;
const int RAIN_WET = 300;

// Warning thresholds
const int SOIL_WARNING_PERCENT = 50;
const int RAIN_WARNING_PERCENT = 50;
const float TILT_WARNING_DEGREES = 15.0;

// MPU6050
const byte MPU_ADDR = 0x68;
bool mpuOK = false;
float baseAX = 0;
float baseAY = 0;
float baseAZ = 1;
float tiltDegrees = 0;
bool tiltWarning = false;

// Barrier state
bool barrierOpen = true;
bool vehicleWasDetected = false;
bool clearTimerRunning = false;
unsigned long vehicleClearStart = 0;

// Sensor readings and alerts
int soilPercent = 0;
int rainPercent = 0;
bool soilWarning = false;
bool rainWarning = false;
bool landslideAlert = false;
bool heavyRainAlert = false;
bool anyAlert = false;

float distanceCM = -1;
bool vehicleDetected = false;


// ==================================================
// CENTERED TEXT
// ==================================================

void drawCentered(const char *text, int y) {
  int width = u8g2.getStrWidth(text);
  int x = (128 - width) / 2;
  if (x < 0) x = 0;
  u8g2.drawStr(x, y, text);
}


// ==================================================
// SENSOR AVERAGE AND PERCENTAGE
// ==================================================

int readAverage(int pin) {
  long total = 0;
  for (int i = 0; i < 10; i++) {
    total += analogRead(pin);
    delay(2);
  }
  return total / 10;
}

int calculatePercent(int raw, int dryValue, int wetValue) {
  if (dryValue == wetValue) return 0;
  int value = map(raw, dryValue, wetValue, 0, 100);
  return constrain(value, 0, 100);
}


// ==================================================
// MPU6050 FUNCTIONS
// ==================================================

bool writeMPU(byte reg, byte value) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readAccel(float &ax, float &ay, float &az) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);

  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ADDR, (byte)6) != 6) return false;

  int16_t rawAX = (int16_t)(
    ((uint16_t)Wire.read() << 8) | Wire.read()
  );
  int16_t rawAY = (int16_t)(
    ((uint16_t)Wire.read() << 8) | Wire.read()
  );
  int16_t rawAZ = (int16_t)(
    ((uint16_t)Wire.read() << 8) | Wire.read()
  );

  ax = rawAX / 16384.0;
  ay = rawAY / 16384.0;
  az = rawAZ / 16384.0;
  return true;
}

void calibrateTilt() {
  Serial.println("Keep model still: calibrating MPU6050");

  float sumX = 0, sumY = 0, sumZ = 0;
  int count = 0;

  for (int i = 0; i < 100; i++) {
    float ax, ay, az;
    if (readAccel(ax, ay, az)) {
      sumX += ax;
      sumY += ay;
      sumZ += az;
      count++;
    }
    delay(20);
  }

  if (count == 0) {
    mpuOK = false;
    Serial.println("MPU6050 calibration failed");
    return;
  }

  baseAX = sumX / count;
  baseAY = sumY / count;
  baseAZ = sumZ / count;

  float magnitude = sqrt(
    baseAX * baseAX + baseAY * baseAY + baseAZ * baseAZ
  );

  if (magnitude > 0.01) {
    baseAX /= magnitude;
    baseAY /= magnitude;
    baseAZ /= magnitude;
  }

  tiltDegrees = 0;
  tiltWarning = false;
  Serial.println("MPU6050 calibration complete");
}

void updateTilt() {
  if (!mpuOK) {
    tiltWarning = false;
    return;
  }

  float ax, ay, az;
  if (!readAccel(ax, ay, az)) return;

  float magnitude = sqrt(ax * ax + ay * ay + az * az);
  if (magnitude < 0.01) return;

  ax /= magnitude;
  ay /= magnitude;
  az /= magnitude;

  float dotProduct =
    ax * baseAX + ay * baseAY + az * baseAZ;

  dotProduct = constrain(dotProduct, -1.0, 1.0);
  tiltDegrees = acos(dotProduct) * 180.0 / PI;
  tiltWarning = tiltDegrees >= TILT_WARNING_DEGREES;
}


// ==================================================
// ULTRASONIC DISTANCE
// ==================================================

float readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 12000UL);
  if (duration == 0) return -1;
  return duration * 0.0343 / 2.0;
}


// ==================================================
// SERVO CONTROL
// ==================================================

void openBarrier() {
  if (!barrierOpen) {
    barrierServo.write(BARRIER_OPEN_ANGLE);
    barrierOpen = true;
    Serial.println("ROAD OPEN");
  }
}

void closeBarrier() {
  if (barrierOpen) {
    barrierServo.write(BARRIER_CLOSED_ANGLE);
    barrierOpen = false;
    Serial.println("ROAD BLOCKED");
  }
}


// ==================================================
// OLED DISPLAY
// Rain only = HEAVY RAIN ALERT
// Soil or tilt = LANDSLIDE ALERT
// ==================================================

void displayOLED() {
  char line[28];
  char tiltText[12];
  dtostrf(tiltDegrees, 4, 1, tiltText);

  u8g2.firstPage();
  do {
    if (landslideAlert) {
      u8g2.setFont(u8g2_font_9x18B_tf);
      drawCentered("LANDSLIDE", 18);

      u8g2.setFont(u8g2_font_7x14B_tf);
      drawCentered("ALERT!", 33);

      u8g2.setFont(u8g2_font_6x12_tf);
      snprintf(line, sizeof(line), "Soil:%d%% Rain:%d%%",
               soilPercent, rainPercent);
      drawCentered(line, 45);

      if (!mpuOK) {
        drawCentered("MPU ERROR", 57);
      } else {
        snprintf(line, sizeof(line), "Tilt:%s deg", tiltText);
        drawCentered(line, 57);
      }

    } else if (heavyRainAlert) {
      u8g2.setFont(u8g2_font_9x18B_tf);
      drawCentered("HEAVY RAIN", 19);

      u8g2.setFont(u8g2_font_7x14B_tf);
      drawCentered("ALERT!", 35);

      u8g2.setFont(u8g2_font_6x12_tf);
      snprintf(line, sizeof(line), "Rain: %d%%", rainPercent);
      drawCentered(line, 48);
      drawCentered("BUZZER ON", 61);

    } else {
      u8g2.setFont(u8g2_font_9x18B_tf);
      drawCentered("SYSTEM", 19);

      u8g2.setFont(u8g2_font_7x14B_tf);
      drawCentered("NORMAL", 34);

      u8g2.setFont(u8g2_font_6x12_tf);
      snprintf(line, sizeof(line), "Soil:%d%% Rain:%d%%",
               soilPercent, rainPercent);
      drawCentered(line, 47);

      if (!mpuOK) {
        drawCentered("MPU ERROR", 60);
      } else {
        snprintf(line, sizeof(line), "Tilt:%s deg | ROAD OPEN",
                 tiltText);
        drawCentered(line, 60);
      }
    }
  } while (u8g2.nextPage());
}


// ==================================================
// SETUP
// ==================================================

void setup() {
  Serial.begin(9600);

  pinMode(SOIL_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  barrierServo.attach(SERVO_PIN);
  barrierServo.write(BARRIER_OPEN_ANGLE);
  barrierOpen = true;

  u8g2.begin();
  Wire.begin();

  mpuOK = writeMPU(0x6B, 0x00);
  if (mpuOK) {
    writeMPU(0x1C, 0x00);
    delay(100);
    calibrateTilt();
  } else {
    Serial.println("MPU6050 not detected!");
  }

  Serial.println("VARODE DISASTER SYSTEM READY");
}


// ==================================================
// MAIN LOOP
// ==================================================

void loop() {
  int soilRaw = readAverage(SOIL_PIN);
  int rainRaw = readAverage(RAIN_PIN);

  soilPercent = calculatePercent(soilRaw, SOIL_DRY, SOIL_WET);
  rainPercent = calculatePercent(rainRaw, RAIN_DRY, RAIN_WET);

  soilWarning = soilPercent >= SOIL_WARNING_PERCENT;
  rainWarning = rainPercent >= RAIN_WARNING_PERCENT;

  updateTilt();

  // Soil or tilt means landslide.
  landslideAlert = soilWarning || (mpuOK && tiltWarning);

  // Rain alone means heavy rain. Landslide has display priority.
  heavyRainAlert = rainWarning && !landslideAlert;

  // Either rain or landslide activates the buzzer and barrier logic.
  anyAlert = landslideAlert || rainWarning;

  distanceCM = readDistanceCM();
  vehicleDetected =
    distanceCM >= 0 && distanceCM <= VEHICLE_DISTANCE_CM;

  digitalWrite(BUZZER_PIN, anyAlert ? HIGH : LOW);

  // ---------- BARRIER LOGIC ----------
  // Both heavy rain and landslide can close the barrier.
  // Original ultrasonic behavior is retained: an object detected
  // during an alert opens the barrier; after it leaves, the
  // barrier closes after the 3-second clear timer.

  if (!anyAlert) {
    openBarrier();
    vehicleWasDetected = false;
    clearTimerRunning = false;
  }
  else if (vehicleDetected) {
    openBarrier();
    vehicleWasDetected = true;
    clearTimerRunning = false;
  }
  else if (vehicleWasDetected) {
    if (!clearTimerRunning) {
      vehicleClearStart = millis();
      clearTimerRunning = true;
      Serial.println("3-second timer started");
    }

    if (millis() - vehicleClearStart >= CLEAR_DELAY_MS) {
      closeBarrier();
      vehicleWasDetected = false;
      clearTimerRunning = false;
    }
  }
  else {
    closeBarrier();
  }

  displayOLED();

  Serial.print("Soil: ");
  Serial.print(soilPercent);
  Serial.print("% | Rain: ");
  Serial.print(rainPercent);
  Serial.print("% | Tilt: ");
  Serial.print(tiltDegrees, 1);
  Serial.print(" deg | Alert: ");

  if (landslideAlert) {
    Serial.print("LANDSLIDE");
  } else if (heavyRainAlert) {
    Serial.print("HEAVY RAIN");
  } else {
    Serial.print("NORMAL");
  }

  Serial.print(" | Buzzer: ");
  Serial.print(anyAlert ? "ON" : "OFF");
  Serial.print(" | Barrier: ");
  Serial.println(barrierOpen ? "OPEN" : "BLOCKED");

  delay(100);
}
