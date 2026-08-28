#include <Arduino.h>

// function prototype
int voltage(float analogvalue);

// Put your potentiometer pin assignment here
const int sensorPin = 0;

void setup() {
    Serial.begin(115200);
}

void loop() {
    // This is the line for printing in the serial
    Serial.println(voltage(analogRead(sensorPin)));
    delay(50); 
}

// function to calculate output voltage
int voltage(float analogvalue){
    int voltage;
    //analogRead(sensorPin); gives us 0-4095 values
    //use the formula (Analog value*Reference voltage) / (Sensor Resolution) to calculate the output voltage
    return voltage;
}