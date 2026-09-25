# Lab 5: Integration Exploration

**Name:** Ayan Sheikh, **Case ID** ams926

**Course:** ECSE395 

## Assignment Overview

This project combines a digital touch sensor, an Adafruit Feather ESP32 V2, an L9110 motor driver, a TT DC gear motor, and an LED. Touching the sensor selects one motor direction; releasing it selects the other. The program increases the PWM command while each state remains active, up to a value of 255. The LED is on while touch is detected and off when the sensor is not touched.

The ESP32 controls the motor driver inputs; the motor must be powered through the motor-driver circuit, not directly from an ESP32 GPIO pin.

## Repository Contents

- [`src/main.cpp`](src/main.cpp): pin assignments, input/output initialization, touch-state checks, LED behavior, motor direction selection, and PWM speed ramps.
- [`platformio.ini`](platformio.ini): PlatformIO environment for the Adafruit Feather ESP32 V2 and Arduino framework, with the serial monitor set to 115200 baud.
- [`README.md`](README.md): general project and PlatformIO setup information.

- [`integration exploration.md`](integration%20exploration.md): this lab report and reflection.

There is one cpp program `src/main.cpp`; it contains the program's `setup()` and `loop()` functions.

## Setup and Preparation

### Hardware and Tools

- Adafruit Feather ESP32 V2
- Digital touch sensor module
- TT DC gear motor
- L9110 motor driver
- LED and a current-limiting resistor if using an external LED
- Breadboard and jumper wires
- USB data cable
- Computer with VS Code and the PlatformIO extension
- Motor power source appropriate for the motor and driver

### Wiring Reference

| Part | ESP32 / circuit connection | Purpose |
| --- | --- | --- |
| Touch sensor signal | A2 | Digital touch input; the code treats HIGH as touched |
| L9110 input 1A | A1 | PWM input for the touch-selected direction |
| L9110 input 2A | A0 | PWM input for the untouched-selected direction |
| LED control | GPIO 13 | Turns on when touched and off when untouched |
| Grounds | ESP32, sensor, and motor-driver ground connected together | Provides a shared signal reference |
| TT motor | L9110 motor output terminals | Motor-driver output; do not connect the motor directly to ESP32 pins |

Connect the touch sensor's power and ground according to its module documentation. ESP32 GPIO is 3.3 V logic; make sure the sensor signal does not exceed the ESP32's permitted input voltage. For an external LED, connect GPIO 13 through a suitable current-limiting resistor to the LED, then connect the LED to ground with the correct polarity. Check the motor and driver supply requirements before powering the motor, and double-check wiring for shorts.

The rotation direction depends on the motor's lead orientation and driver wiring. The labels "counterclockwise" and "clockwise" in the serial messages must be confirmed by observing the assembled motor; swap the motor leads or driver-channel mapping if the physical directions are reversed.

## Steps to Complete the Lab

### (a) Setup and Preparation

1. Assemble the Feather ESP32 V2, touch sensor, LED, L9110 driver, and TT motor using the wiring reference above.
2. Keep the motor disconnected from power while checking the signal wiring. Confirm the motor is connected to the L9110 outputs, not to ESP32 GPIO.
3. Connect the sensor signal to A2, L9110 input 1A to A1, L9110 input 2A to A0, and LED control to GPIO 13. Connect circuit grounds together.
4. Connect the ESP32 to the computer with a data-capable USB cable.
5. Open this project folder in VS Code. Check that `platformio.ini` selects `adafruit_feather_esp32_v2` and the Arduino framework.
6. Open `src/main.cpp` and check that its pin assignments match the actual wiring.

### (b) In-Class Task

1. Build the project with PlatformIO and resolve any reported compiler errors.
2. Upload the firmware to the ESP32.
3. Open the serial monitor at 115200 baud.
4. With the motor supply enabled, check that the serial message, LED, and motor response agree when the touch sensor is touched and released.
5. Confirm the actual rotation directions. If the motor's direction differs from the message, adjust the motor wiring or channel mapping, then rebuild and upload again.
6. Observe the speed ramp in each state. The code starts each state at PWM 128 and increases it by one approximately every 45 ms until it reaches 255.
7. Record the wiring, observations, and any changes made to the circuit or program.


### (c) Documentation

Document the final wiring, the observed motor directions, whether the touch sensor reads HIGH when touched, and any differences between expected and observed behavior. Use the photo-evidence section below for clear views of the completed setup.

## Uploading the Code to the ESP32

### Tools Used

- VS Code with the PlatformIO extension
- PlatformIO project environment `adafruit_feather_esp32_v2`
- USB data cable
- PlatformIO Serial Monitor at 115200 baud

### Upload Process

1. Open the `Lab 5` project folder in VS Code.
2. Connect the ESP32 by USB and wait for PlatformIO to detect the project environment.
3. Build first using the PlatformIO **Build** task (the checkmark symbol)
4. Upload using the PlatformIO **Upload** task (the arrow symbol)
5. Open the PlatformIO Serial Monitor (the plug symbol)
6. Touch and release the sensor while observing the serial output, LED, and motor. Disconnect power before changing wiring.

## How the System Works

At the start of each pass through `loop()`, the ESP32 reads the touch sensor on A2. The firmware treats HIGH as touched and LOW as untouched.

- **Touched (HIGH):** The code turns the LED on, sets motor input 2A (A0) to zero, and applies increasing PWM to input 1A (A1). It checks the sensor repeatedly and continues the ramp while the sensor remains HIGH.
- **Not touched (LOW):** The code turns the LED off, sets motor input 1A (A1) to zero, and applies increasing PWM to input 2A (A0). It continues while the sensor remains LOW.
- **Speed command:** Each direction starts with a local `motorSpeed` value of 128. The value increases by one every loop iteration, which includes a 45 ms delay, until it reaches 255. The PWM output is written after the limit check, so 255 is written and maintained while that state continues.
- **State change:** When the sensor changes state, the current `while` loop ends and the other direction branch takes over. That branch starts its own speed ramp at 128.

The code's direction names are assumptions based on the intended wiring; confirm clockwise and counterclockwise rotation on the physical system. The firmware also assumes the touch module provides a stable digital HIGH/LOW output.

## System Proof: Photos

### Touch Sensor Circuit

![Touch sensor circuit setup](./media/touch_circuit.jpg)

### TT Motor Circuit

![TT motor and motor-driver circuit setup](./media/ttmotor_circuit.jpg)

### Power Supply

![Power supply used for the motor circuit](./media/power_supply.jpg)

## Time Reporting and Reflection

- **Time spent:** 1.5 hours (reported for this assignment).
- **Difficulty:** Low.
- **Reflection:** 
- **Course comfort:** Comfortable with the course content
- **Additional feedback:** N/A.
