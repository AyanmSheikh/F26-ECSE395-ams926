#include <Arduino.h>
// This is required in PlatformIO but hidden in the standard Arduino IDE.

#define LED_PIN 13

void setup() {
  pinMode(LED_PIN, OUTPUT); // ams926 Set the LED pin as an output
  Serial.begin(115200); // ams926 Start the Serial connection at 115200 baud
  // TODO: Define your baud rates
  
}

void loop() {
  // TODO: Define your text output
  // Serial.println("_____"); // Print the words to the Serial Monitor.
  Serial.println("HELLO WORLD");   // ams926 Print the words to the Serial Monitor.
  
  // TODO: Set up your delay in milliseconds
  digitalWrite(LED_PIN, HIGH); // ams926 LED On
  delay(1000); // ams926 Wait for 1 second
  digitalWrite(LED_PIN, LOW); // ams926 LED Off
  delay(1000); // ams926 Wait for 1 second
  
}