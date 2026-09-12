#include <Arduino.h>

// function prototype
float voltage(float analogvalue);

// Put your potentiometer pin assignment here
const int sensorPin = A1; // ams926 this assigns IO pin of potentiometer to A1
/*
void setup() {
    Serial.begin(115200); // ams926 begin serial comm with hardcoded baud
}

void loop() {
    // This is the line for printing in the serial
    Serial.println(voltage(analogRead(sensorPin)));
    delay(50); 
}
*/
// function to calculate output voltage
float voltage(float analogvalue){
    return (analogvalue * 3.3) / 4095; // ams926 this returns the calculated voltage value
}
    