## Playing with sensor
This lab is about connecting a sensor to your ESP32. By completing this lab, you will understand how sensors work and how to read outputs from the sensors. In this lab, we are using potentiometers, which are dial-shaped sensors that can usually be found on radios, cars, or even on your washing machine!

## What is a potentiometer
<img src="images\pot.png" alt="Inside of a potentiometer" width="50%">
You can just imagine a potentiometer as a variable resistor! It has many applications, such as adjusting the brightness of lights and turning the volume of a speaker. While resistors have a certain value that stays the same, potentiometers can change their resistance by only twisting the knob! How nifty is that!

## Usefull resources
If you are not sure how to complete this lab, first, try to find any online resources, such as [ESP32IO](https://esp32io.com/tutorials/esp32-potentiometer). Or you may find the README document of Lab 2 helpful! Or if you run into any issues, ask your neighbor or TA!

## How to complete this lab?
* Step 1: Clone this repository and use PlatformIO to open this project
* Step 2: Read the manual carefully and make sure you understand the requirements
* Step 3: Connect your ESP32 to the sensor
    + Reference the website and put your circuit together!
* Step 4: Modify the code "value.cpp"
    + Serial.println(??) <-- we want to print a value in the serial monitor, what do we need to add?
* Step 5: Upload the code to your ESP32 and open the serial monitor. What do you see?
* Step 6: Modify the code "voltage.cpp"
    + Calculate the voltage output of the potentiometer, follow the prompt of the code comment
* Step 7: Upload the code to your ESP32 and open the serial monitor again.

## Troubleshooting
* I cannot connet to my ESP32!
    + Try to switch to another cable that has data transfer capability.
    + Did you select the right USB COM#?
    + Did you setup the project right? Did you select the right board (Adafruit Feather ESP32 V2)?
* I cannot see/cannot read output in my serial monitor!
    + Did you setup your baud rate right?
    + Did you connect your sensor and ESP32 correctly?
* My output is an integer, not a float!
    + Inspect the data type of your variable