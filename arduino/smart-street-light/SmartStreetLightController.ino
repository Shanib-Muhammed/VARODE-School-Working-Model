/*
  Smart Street Light Controller
  Board: Arduino Nano

  US1: TRIG D2, ECHO D3
  US2: TRIG D4, ECHO D5

  LEDs:
  LED 1 = D6
  LED 2 = D7
  LED 3 = D8
  LED 4 = D9
  LED 5 = D10

  LDR = A0

  Behaviour (only when dark):
  US1 -> LEDs 1 to 5 ON
  US2 -> LEDs 1 to 5 OFF
  US2 -> LEDs 5 to 1 ON
  US1 -> LEDs 5 to 1 OFF
*/

const byte TRIG1 = 2;
const byte ECHO1 = 3;
const byte TRIG2 = 4;
const byte ECHO2 = 5;

const byte LEDS[5] = {6, 7, 8, 9, 10};
const byte LDR_PIN = A0;

const int NIGHT_THRESHOLD = 400;
const int DETECT_DISTANCE_CM = 5;
const int RELEASE_DISTANCE_CM = 8;

const unsigned long LED_STEP_MS = 200;
const unsigned long SENSOR_INTERVAL_MS = 100;

enum SystemState {
  IDLE,
  FORWARD_LIGHTS_ON,
  REVERSE_LIGHTS_ON
};

SystemState systemState = IDLE;

bool animationRunning = false;
bool animationReverse = false;
bool animationTurnOn = true;
byte animationIndex = 0;

unsigned long lastLedStep = 0;
unsigned long lastSensorRead = 0;

bool sensor1Latched = false;
bool sensor2Latched = false;

void allLightsOff() {
  for (byte i = 0; i < 5; i++) {
    digitalWrite(LEDS[i], LOW);
  }

  animationRunning = false;
  animationIndex = 0;
}

int readDistance(byte trig, byte echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(3);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);

  unsigned long duration = pulseIn(echo, HIGH, 18000UL);

  if (duration == 0) {
    return -1;
  }

  return duration / 58;
}

bool detectObject(int distance, bool &latched) {
  if (distance < 0) {
    return false;
  }

  if (distance >= RELEASE_DISTANCE_CM) {
    latched = false;
  }

  if (distance <= DETECT_DISTANCE_CM && !latched) {
    latched = true;
    return true;
  }

  return false;
}

void startSequence(bool reverse, bool turnOn) {
  animationReverse = reverse;
  animationTurnOn = turnOn;
  animationIndex = 0;
  animationRunning = true;
  lastLedStep = millis();
}

void updateSequence() {
  if (!animationRunning) {
    return;
  }

  if (millis() - lastLedStep < LED_STEP_MS) {
    return;
  }

  lastLedStep = millis();

  byte index = animationReverse ? 4 - animationIndex : animationIndex;

  digitalWrite(LEDS[index], animationTurnOn ? HIGH : LOW);
  animationIndex++;

  if (animationIndex >= 5) {
    animationRunning = false;
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(TRIG1, OUTPUT);
  pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT);
  pinMode(ECHO2, INPUT);
  pinMode(LDR_PIN, INPUT);

  for (byte i = 0; i < 5; i++) {
    pinMode(LEDS[i], OUTPUT);
    digitalWrite(LEDS[i], LOW);
  }

  Serial.println("Smart Street Light Controller Ready");
}

void loop() {
  int lightValue = analogRead(LDR_PIN);
  bool isNight = (lightValue < NIGHT_THRESHOLD);

  if (!isNight) {
    allLightsOff();
    systemState = IDLE;
    sensor1Latched = false;
    sensor2Latched = false;
    return;
  }

  // Finish the current animation before accepting another trigger.
  updateSequence();

  if (animationRunning) {
    return;
  }

  if (millis() - lastSensorRead < SENSOR_INTERVAL_MS) {
    return;
  }

  lastSensorRead = millis();

  int distance1 = readDistance(TRIG1, ECHO1);
  int distance2 = readDistance(TRIG2, ECHO2);

  bool hit1 = detectObject(distance1, sensor1Latched);
  bool hit2 = detectObject(distance2, sensor2Latched);

  if (hit1) {
    if (systemState == IDLE) {
      Serial.println("US1: LEDs 1 to 5 ON");
      startSequence(false, true);
      systemState = FORWARD_LIGHTS_ON;
    }
    else if (systemState == REVERSE_LIGHTS_ON) {
      Serial.println("US1: LEDs 5 to 1 OFF");
      startSequence(true, false);
      systemState = IDLE;
    }
  }

  else if (hit2) {
    if (systemState == IDLE) {
      Serial.println("US2: LEDs 5 to 1 ON");
      startSequence(true, true);
      systemState = REVERSE_LIGHTS_ON;
    }
    else if (systemState == FORWARD_LIGHTS_ON) {
      Serial.println("US2: LEDs 1 to 5 OFF");
      startSequence(false, false);
      systemState = IDLE;
    }
  }
}
