#include <Arduino.h>
// This is required in PlatformIO but hidden in the standard Arduino IDE.

#define LED_PIN 13

void setup() {
  pinMode(LED_PIN, OUTPUT);
  Serial.begin(115200); // Start the Serial connection at 115200 baud
  // TODO: Define your baud rates
  
}

void loop() {
  // TODO: Define your text output
  // Serial.println("_____"); // Print the words to the Serial Monitor.
  Serial.println("HELLO WORLD");  
  
  // TODO: Set up your delay in milliseconds
  digitalWrite(LED_PIN, HIGH); // LED On
  delay(1000);
  digitalWrite(LED_PIN, LOW); // LED Off
  delay(1000);
  
}