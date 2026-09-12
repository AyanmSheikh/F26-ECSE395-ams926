#include <Arduino.h>

//Put your potentiometer pin assignment here
const int sensorPin = A1; 

float voltage(float analogvalue);

void setup() {
  Serial.begin(115200);
}

void loop() {
  //This line should print out the values from the sensor by Serial.println(??);
  int sensorValue = analogRead(sensorPin); // ams926 reads analog value from potentiometer
  float sensorVoltage = voltage(sensorValue); // ams926 converts analog reading to voltage
  Serial.println(sensorVoltage); // ams926 prints voltage to serial monitor

  delay(100); // ams926 waits 100 ms before looping
}
