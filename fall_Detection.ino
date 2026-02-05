#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>

// --- USER CONFIGURATION (PRESERVED) ---
const char* ssid = "POCO X6 5G";           
const char* password = "0123456789";       
const char* udpAddress = "10.98.184.30";  
const int udpPort = 4210;

// Hardware Pins
const int LED_PIN = 15;
const int BUTTON_PIN = 5;

WiFiUDP udp;

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // 1. Initialize I2C with your verified pins
  Wire.begin(21, 22); 
  delay(1000);

  Serial.println("Waking up MPU6050 directly...");
  
  // 2. Direct Wakeup (This bypassed the "Not Found" error)
  Wire.beginTransmission(0x68);
  Wire.write(0x6B); // Power management register
  Wire.write(0);    // Wake up command
  if (Wire.endTransmission() == 0) {
    Serial.println("✅ Sensor is Awake!");
  } else {
    Serial.println("❌ Critical Error: Sensor not responding.");
    while(1) delay(10);
  }

  // 3. WiFi Connection
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\n✅ WiFi Connected!");
  
  digitalWrite(LED_PIN, HIGH); delay(500); digitalWrite(LED_PIN, LOW);
}

void loop() {
  // 4. Read Raw Data Directly (Same method as your successful test)
  Wire.beginTransmission(0x68);
  Wire.write(0x3B); 
  Wire.endTransmission(false);
  Wire.requestFrom(0x68, 6, true);

  int16_t rawX = Wire.read() << 8 | Wire.read();
  int16_t rawY = Wire.read() << 8 | Wire.read();
  int16_t rawZ = Wire.read() << 8 | Wire.read();

  // Convert to m/s^2 (Approximate)
  float ax = (rawX / 16384.0) * 9.81;
  float ay = (rawY / 16384.0) * 9.81;
  float az = (rawZ / 16384.0) * 9.81;

  // 5. Send Data to Laptop
  String packet = String(ax) + "," + String(ay) + "," + String(az);
  udp.beginPacket(udpAddress, udpPort);
  udp.print(packet);
  udp.endPacket();

  // 6. Listen for "FALL" Alarm from Laptop
  int packetSize = udp.parsePacket();
  if (packetSize) {
    char incoming[255];
    int len = udp.read(incoming, 255);
    if (len > 0) incoming[len] = 0;
    
    if (String(incoming) == "FALL") {
      Serial.println("⚠️ ALARM! Fall Detected on Laptop.");
      digitalWrite(LED_PIN, HIGH);
      delay(2000); 
      digitalWrite(LED_PIN, LOW);
    }
  }
  delay(15); 
}
