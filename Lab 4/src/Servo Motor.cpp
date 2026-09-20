#include <ESP32Servo.h>
// Don't forget to include the library!!
// From PlatfromIO library, search for ESP32 servo and add it to the project
/*
// Define the servo and the pin it is connected to, what is your servo pin?
Servo myServo;
const int servoPin = 26; //ams926 pin A0

// Define the minimum and maximum pulse widths for the servo
const int minPulseWidth = 500; // ams926 (500)0.5 ms ----> (100) .1 ms longer pauses at one angle
const int maxPulseWidth = 2500; // (2500) 2.5 ms --------> (5000) 5.0 ms longer puases at the other angle ----------> 750 really short , slow pulses with longer paues
//ams926 the wider the difference between the min and max, the more the servo will rotate
void setup() {
  // Attach the servo to the specified pin and set its pulse width range
  myServo.attach(servoPin, minPulseWidth, maxPulseWidth);

  // Set the PWM frequency for the servo
  myServo.setPeriodHertz(50); // ams926 Standard 50Hz servo ------> 750Hz, shorter faster pulses with less rotation, --> 10Hz, slower, shoppier pulses, with more rotation
}

void loop() {
  // ams926 Rotate the servo from 0 to 180 degrees ----> 90 degrees, shorter rotation
  for (int angle = 0; angle <= 90; angle++) {
    int pulseWidth;
    // the map function is a puction that maps 0 degrees to 500 pulse width, and 180 degrees to 2500 pulse width
    // map(angle, min angle, max angle, min pulse width, max pulse width)
    pulseWidth = map(angle, 0, 180, minPulseWidth, maxPulseWidth);
    myServo.writeMicroseconds(pulseWidth);
    delay(20); // the biger the delay, the slower it rotates
  }

  // ams926 Rotate the servo from 180 to 0 degrees ----> 90 degrees shorter rotation
  for (int angle = 90; angle >= 0; angle--) {
    int pulseWidth;
    // the map function is a puction that maps 0 degrees to 500 pulse width, and 180 degrees to 2500 pulse width
    // map(angle, min angle, max angle, min pulse width, max pulse width)
    pulseWidth = map(angle, 0, 180, minPulseWidth, maxPulseWidth); // ams926 the last 4 inputs control the speed, first controls the angle
    myServo.writeMicroseconds(pulseWidth);
    delay(20); // the biger the delay, the slower it rotate
  }
}
  */