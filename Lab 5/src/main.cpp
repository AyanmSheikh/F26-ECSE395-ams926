#include <Arduino.h>

// ams926: Pin assignments for the touch sensor, status LED, and L9110 motor inputs.
const int sensorPin = A2;
const int ledPin = 13;

const int MOTOR_B_1A = A1;
const int MOTOR_B_2A = A0;

void setup() {
  // ams926: Start serial output and configure the sensor, LED, and motor-driver pins.
  Serial.begin(115200);
  pinMode(sensorPin, INPUT);
  Serial.println("Sensor Pin initialized to input");
  pinMode(ledPin, OUTPUT);
  pinMode(MOTOR_B_1A, OUTPUT);
  pinMode(MOTOR_B_2A, OUTPUT);
  Serial.println("Motor Pins initialized to output");
}

void loop() {
  // ams926: Read the digital touch-sensor state; this program treats HIGH as touched.
  int sensorValue = digitalRead(sensorPin);

  if (sensorValue == HIGH) {
    // ams926: While touched, drive input 1A with PWM and keep input 2A low.
    Serial.println("Touch detected! Rotating Counterclockwise!");
    int motorSpeed = 128;
    analogWrite(MOTOR_B_2A, 0);
    digitalWrite(ledPin, HIGH);

    // ams926: Ramp PWM toward full duty while the sensor continues to read HIGH.
    while (sensorValue == HIGH) {
      sensorValue = digitalRead(sensorPin);
      if (motorSpeed < 255) {
        motorSpeed++;
      }
      analogWrite(MOTOR_B_1A, motorSpeed);
      delay(45);
    }
  } else {
    // ams926: While untouched, drive input 2A with PWM and keep input 1A low.
    Serial.println("No touch detected! Rotating Clockwise!");
    int motorSpeed = 128;
    analogWrite(MOTOR_B_1A, 0);
    digitalWrite(ledPin, LOW);

    // ams926: Ramp PWM toward full duty while the sensor continues to read LOW.
    while (sensorValue == LOW) {
      sensorValue = digitalRead(sensorPin);
      if (motorSpeed < 255) {
        motorSpeed++;
      }
      analogWrite(MOTOR_B_2A, motorSpeed);
      delay(45);
    }
  }

  // ams926: Brief pause before checking the new sensor state in the next pass.
  delay(50);
}




