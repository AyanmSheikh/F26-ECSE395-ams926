# Lab 3 readme | Playing with sensors

In this lab we will use platformIO to connect to a circuit with a potentiometer and touch sensor, I have a macbook pro and USB-C data capable cable

## Repo layout

In this folder of Lab 3 the src folder has code for the code for the potentiometer, resolution -> voltage calculation (voltage.cpp), and touch.cpp for touch sensor. The platform.ini file serves as a config for the io program to initialize its state before uploading code to ESP32, the markdown provides **documentation for this lab** and the rest of the folders are not that important to note.
```text
Lab 3/
├── src/
│   ├── potentiometer.cpp
│   │   
│   ├── touch.cpp
│   │
│   └── voltage.cpp
│
├── platform.ini
│   
└── playing with sensors.md
```

## Running the Code

To get the code running on your ESP32, make sure it is connected via USB-C, the ESP32 should be connected to a bread board and the corresponding communication pins (A1) as well as power (3V) and Ground (GND) to either the potentiometer or the touch sensor. Depending on which code you choose to run and what device you have hooked up to the ESP32 physically you must comment out the other .cpp files' setup() and loop() methods with /* .....*/ in order for the code to upload to the ESP32 without a fatal error. 

## Time Reporting and Reflection 


1. How long did it take you to complete this assignment?
- 1 hour and 10 minutes, I did not have a touch sensor and had to walk to lab partners apartment to borrow one.
2. What level of difficulty would you associate with this assignment?
- [x] Low
- [ ] Medium
- [ ] High
3. If you associated medium/high difficulty with this assignment, what aspect did you
find the most difficult?
- I didn't
4. How comfortable do you currently feel with the course content?
- Comfortable, a little heavy with the workload but not hard things
5. Do you have any additional information or feedback you would like to share with
the instructors?
- I do not like the take home portions of the lab, we should have enough time to complete a lab during the 50 minutes of lab time,otherwise we should have more lab time.