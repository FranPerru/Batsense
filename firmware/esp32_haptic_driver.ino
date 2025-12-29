/*
 * Batsense - Haptic Feedback Firmware
 * ----------------------------------
 * This script runs on an ESP32 to control a vibration motor 
 * based on HTTP requests sent by the Batsense Vision System.
 */

#include <WiFi.h>
#include <WebServer.h>

// --- CONFIGURATION ---
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

// Define the GPIO pin where your vibration motor is connected
// In your images, verify which pin you are using (e.g., GPIO 12 or 13)
const int VIBRATOR_PIN = 13; 

// PWM Settings
const int freq = 5000;
const int vibratorChannel = 0;
const int resolution = 8; // 0-255 range

WebServer server(80);

// --- HANDLERS ---

void handleVibration() {
  if (server.hasArg("intensity")) {
    String intensityVal = server.arg("intensity");
    int intensityPercent = intensityVal.toInt(); // 0 to 100
    
    // Map 0-100% to 0-255 for PWM
    int pwmValue = map(intensityPercent, 0, 100, 0, 255);
    
    ledcWrite(vibratorChannel, pwmValue);
    
    Serial.print("Vibration Intensity Received: ");
    Serial.print(intensityPercent);
    Serial.println("%");
    
    server.send(200, "text/plain", "OK");
  } else {
    server.send(400, "text/plain", "Missing intensity argument");
  }
}

void setup() {
  Serial.begin(115200);

  // Configure PWM for the motor
  ledcSetup(vibratorChannel, freq, resolution);
  ledcAttachPin(VIBRATOR_PIN, vibratorChannel);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());

  /* * SETUP ROUTES
   * IMPORTANT: Update the path below to match the specific 
   * role of this ESP32 (e.g., "/red/player", "/red/goal", etc.)
   */
  server.on("/red/player", HTTP_GET, handleVibration); 
  server.on("/red/goal", HTTP_GET, handleVibration);
  server.on("/blue/player", HTTP_GET, handleVibration);
  server.on("/blue/goal", HTTP_GET, handleVibration);

  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}
