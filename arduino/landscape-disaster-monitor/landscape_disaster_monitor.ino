#include <Wire.h>
#include <U8g2lib.h>

// OLED: SDA -> D2, SCL -> D3
U8G2_SSD1306_128X64_NONAME_1_SW_I2C u8g2(
  U8G2_R0,
  3,  // SCL
  2,  // SDA
  U8X8_PIN_NONE
);

// Analog sensor pins
const int SOIL_PIN = A0;
const int RAIN_PIN = A1;

// Calibrate these values for your sensors
const int SOIL_DRY = 800;
const int SOIL_WET = 350;

const int RAIN_DRY = 900;
const int RAIN_WET = 300;

// Warning threshold
const int SOIL_WARNING_THRESHOLD = 50;
const int RAIN_WARNING_THRESHOLD = 50;

int soilRaw = 0;
int rainRaw = 0;

int soilPercent = 0;
int rainPercent = 0;

// Read average to reduce small fluctuations
int readAverage(int pin) {
  long total = 0;

  for (int i = 0; i < 10; i++) {
    total += analogRead(pin);
    delay(5);
  }

  return total / 10;
}

// Convert raw analog reading to percentage
int calculatePercent(int raw, int dryValue, int wetValue) {
  if (dryValue == wetValue) {
    return 0;
  }

  int percent = map(raw, dryValue, wetValue, 0, 100);
  return constrain(percent, 0, 100);
}

// Draw text centered horizontally
void drawCentered(const char* text, int y) {
  int width = u8g2.getStrWidth(text);
  int x = (128 - width) / 2;

  if (x < 0) {
    x = 0;
  }

  u8g2.drawStr(x, y, text);
}

// Display OLED screen
void displayOLED() {
  bool soilWarning = soilPercent >= SOIL_WARNING_THRESHOLD;
  bool rainWarning = rainPercent >= RAIN_WARNING_THRESHOLD;
  bool warning = soilWarning || rainWarning;

  char values[30];

  snprintf(values, sizeof(values),
           "Soil:%d%% Rain:%d%%",
           soilPercent, rainPercent);

  u8g2.firstPage();

  do {
    if (warning) {
      const char* line1;

      if (soilWarning && rainWarning) {
        line1 = "LANDSLIDE";
      } else if (soilWarning) {
        line1 = "SOIL WET";
      } else {
        line1 = "HEAVY RAIN";
      }

      // Large alert text
      u8g2.setFont(u8g2_font_9x18B_tf);
      drawCentered(line1, 25);
      drawCentered("WARNING!", 46);

      // Small sensor values at bottom
      u8g2.setFont(u8g2_font_5x8_tf);
      drawCentered(values, 63);

    } else {
      // Normal screen
      u8g2.setFont(u8g2_font_6x10_tf);
      drawCentered("SYSTEM NORMAL", 15);

      char soilText[24];
      char rainText[24];

      snprintf(soilText, sizeof(soilText),
               "Soil: %d%%", soilPercent);

      snprintf(rainText, sizeof(rainText),
               "Rain: %d%%", rainPercent);

      drawCentered(soilText, 34);
      drawCentered(rainText, 49);
    }

  } while (u8g2.nextPage());
}

void setup() {
  Serial.begin(115200);

  pinMode(SOIL_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);

  u8g2.begin();

  Serial.println("Varode Landscape Disaster Monitor");
  Serial.println("Water-level sensor disabled");
  Serial.println("MPU6050 disabled");
}

void loop() {
  // Read sensors
  soilRaw = readAverage(SOIL_PIN);
  rainRaw = readAverage(RAIN_PIN);

  // Calculate percentages
  soilPercent = calculatePercent(
    soilRaw, SOIL_DRY, SOIL_WET
  );

  rainPercent = calculatePercent(
    rainRaw, RAIN_DRY, RAIN_WET
  );

  // Update display
  displayOLED();

  // Serial Monitor output
  Serial.print("Soil Raw: ");
  Serial.print(soilRaw);
  Serial.print(" | Soil: ");
  Serial.print(soilPercent);
  Serial.println("%");

  Serial.print("Rain Raw: ");
  Serial.print(rainRaw);
  Serial.print(" | Rain: ");
  Serial.print(rainPercent);
  Serial.println("%");

  if (soilPercent >= SOIL_WARNING_THRESHOLD &&
      rainPercent >= RAIN_WARNING_THRESHOLD) {
    Serial.println("ALERT: LANDSLIDE WARNING!");
  } else if (soilPercent >= SOIL_WARNING_THRESHOLD) {
    Serial.println("WARNING: SOIL WET");
  } else if (rainPercent >= RAIN_WARNING_THRESHOLD) {
    Serial.println("WARNING: HEAVY RAIN");
  } else {
    Serial.println("STATUS: NORMAL");
  }

  Serial.println("-------------------------");
  delay(300);
}
