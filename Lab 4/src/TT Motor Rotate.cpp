#include <Arduino.h>

// TODO: Define your pins
// Hint: Look at your wiring. Which pins did you use?
const int MOTOR_B_1A = 26; //ams926
const int MOTOR_B_1B = 25; //ams926

void setup() {
  // TODO: Initialize Serial communication
  Serial.begin(115200); //ams926 115200 is the baud rate, which is the speed of communication between the ESP32 and the computer. It is a standard value for serial communication. The higher the baud rate, the faster the data transfer, but it may also lead to more errors if the connection is not stable. 115200 is a good balance between speed and reliability for most applications.

  // TODO: Set your motor pins as OUTPUTs
  pinMode(MOTOR_B_1A, OUTPUT); // ams926 pinmode sets the specific pins defined in the program as variables to output
  pinMode(MOTOR_B_1B, OUTPUT);

  Serial.println("Pins initialized to output"); //ams926 print message to terminal
}

void loop() {
  // --- SECTION 1: Clokwise (5s) ---
  Serial.println("Rotating Clockwise for 5 seconds");//ams926 print message to terminal
  
  // TODO: Write HIGH to one pin and LOW to the other
  digitalWrite(MOTOR_B_1A, HIGH); // ams926, by setting one pin to HIGH and the other to LOW, the motor will rotate in one direction. If you reverse the pins, the motor will rotate in the opposite direction.
  digitalWrite(MOTOR_B_1B, LOW);
  
  delay(5000);// ams926 delay for specific time

  // --- SECTION 2: Stop (2s) ---
  Serial.println("Stopping for 2 seconds");//ams926 print message to terminal
  
  // TODO: Turn off the motor
  digitalWrite(MOTOR_B_1A, LOW);//ams926 both pins low stops the motor from rotating
  digitalWrite(MOTOR_B_1B, LOW);

  delay(2000);// ams926 delay for specific time

  // --- SECTION 3: Counterclockwise (5s) ---
  Serial.println("Rotating Counterclockwise for 5 seconds");//ams926 print message to terminal

  // TODO: Write HIGH to one pin and LOW to the other
  digitalWrite(MOTOR_B_1A, LOW);// ams926, by setting one pin to HIGH and the other to LOW, the motor will rotate in one direction. If you reverse the pins, the motor will rotate in the opposite direction.
  digitalWrite(MOTOR_B_1B, HIGH);

  delay(5000);// ams926 delay for specific time

  // --- SECTION 4: Stop (2s) ---
  Serial.println("Stopping for 2 seconds");//ams926 print message to terminal
  
  // TODO: Turn off the motor
  digitalWrite(MOTOR_B_1A, LOW);//ams926 both pins low stops the motor from rotating
  digitalWrite(MOTOR_B_1B, LOW);

  delay(2000);
}// ams926 delay for specific time


// Note:
// - Please uncomment the necessary lines and fill in the blank to complete the assignment.