// ==========================================
// ESP8266 Autonomous Slow Car
// L298N + 2 DC Motors + HC-SR04
// ==========================================

// ---------- L298N Motor Driver ----------
#define ENA D3
#define IN1 D1
#define IN2 D2

#define ENB D4
#define IN3 D5
#define IN4 D6

// ---------- Ultrasonic Sensor ----------
#define TRIG_PIN D7
#define ECHO_PIN D8

// ---------- Settings ----------
const int SAFE_DISTANCE = 15;   // Start slowing below this distance
const int STOP_DISTANCE = 8;    // Stop at 8 cm or less

// Very slow motor speed
const int MAX_SPEED = 70;
const int MIN_SPEED = 25;

void setup() {

  Serial.begin(115200);

  // Motor pins
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Ultrasonic pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Start stopped
  stopCar();

  Serial.println();
  Serial.println("================================");
  Serial.println("   AUTONOMOUS CAR STARTING");
  Serial.println("================================");

  delay(2000);
}

void loop() {

  float distance = getDistance();

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");

  // --------------------------------
  // NO VALID READING
  // --------------------------------
  if (distance <= 0) {
    Serial.println("Ultrasonic reading error");
    stopCar();
    delay(100);
    return;
  }

  // --------------------------------
  // OBSTACLE VERY CLOSE
  // --------------------------------
  if (distance <= STOP_DISTANCE) {

    stopCar();

    Serial.println("!!! OBSTACLE DETECTED !!!");
    Serial.println("CAR STOPPED");

  }

  // --------------------------------
  // OBSTACLE GETTING CLOSE
  // --------------------------------
  else if (distance <= SAFE_DISTANCE) {

    int speedValue = map(
      distance,
      STOP_DISTANCE,
      SAFE_DISTANCE,
      MIN_SPEED,
      MAX_SPEED
    );

    speedValue = constrain(speedValue, MIN_SPEED, MAX_SPEED);

    moveForward(speedValue);

    Serial.print("CAR SLOWING - SPEED: ");
    Serial.println(speedValue);
  }

  // --------------------------------
  // CLEAR ROAD
  // --------------------------------
  else {

    moveForward(MAX_SPEED);

    Serial.println("CAR MOVING FORWARD");
  }

  delay(100);
}


// ==========================================
// GET DISTANCE FROM HC-SR04
// ==========================================

float getDistance() {

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return -1;
  }

  float distance = duration * 0.0343 / 2;

  return distance;
}


// ==========================================
// MOVE FORWARD
// ==========================================

void moveForward(int speedValue) {

  // Motor A
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);

  // Motor B
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  // Speed control
  analogWrite(ENA, speedValue);
  analogWrite(ENB, speedValue);
}


// ==========================================
// STOP CAR
// ==========================================

void stopCar() {

  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);

  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}
