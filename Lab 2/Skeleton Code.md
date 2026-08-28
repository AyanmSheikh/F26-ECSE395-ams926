```
#include <Arduino.h>
// This is required in PlatformIO but hidden in the standard Arduino IDE.

#define LED_PIN 13

void setup() {
  pinMode(LED_PIN, OUTPUT);
  // TODO: Define your baud rates
  // Serial.begin(_____); // Start the Serial connection
}

void loop() {
  // TODO: Define your text output
  // Serial.println("_____"); // Print the words to the Serial Monitor.
  
  // TODO: Set up your delay in milliseconds
  digitalWrite(LED_PIN, HIGH); // LED On
  // delay(_____); // Speed in milliseconds
  digitalWrite(LED_PIN, LOW); // LED Off
  // delay(_____); // Speed in milliseconds
}
```

- Notes:
	- Please uncomment the necessary lines and fill in the blank to complete the assignment.
	- In `Serial.begin(_____);`
		- `115200` is recommended, but feel free to try it at other baud rates.
		- Baud rate is the speed of data transmission, measuring the number of signal changes per second in communication channel.