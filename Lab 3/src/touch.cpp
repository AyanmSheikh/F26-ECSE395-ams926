#include <Arduino.h>


const int sensorPin = A1; // ams926 this assigns IO pin of touch sensor to A1
const int ledPin = 13; // ams926 this assigns the LED pin to pin 13

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200); // ams926 begin serial comm with hardcoded baud

  pinMode(sensorPin, INPUT); // ams926 this sets the touch sensor pin as an input pin

  pinMode(ledPin, OUTPUT); // ams926 this sets the LED pin as an output pin
}



void loop() {
    int sensorValue = digitalRead(sensorPin); // ams926 this reads the digital value from the touch sensor pin

    if (sensorValue == HIGH) { // ams926 this checks if the touch sensor touched
        Serial.println("Touch detected!"); // ams926 executes print if condition met

        digitalWrite(ledPin, HIGH); // ams926 this sets onboard LED to HIGH 
    } else {
        Serial.println("No touch detected!"); 

        digitalWrite(ledPin, LOW); // ams926 this sets the onboard LED to LOW 
    }  
        
   
    delay(50);
}
