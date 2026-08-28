## Blink
The first and most basic program that you can upload to your board is the classic Blink sketch. This takes something on the board and makes it, well, blink! On and off. It's a great way to make sure everything is working and you're uploading your sketch to the right board and right configuration.

## Checklist
To check that you have all the necessary components.
### Hardware
- ESP32 (Adafruit Feather V2)
- USB Cable (making sure that is not charging only)
### Software
This step you have to install PlatformIO IDE extension (assumes that you have VS Code installed from Lab #1).
- Open VS Code
- Click on the **Extensions** icon in the left sidebar (or press `Ctrl+Shift+X` or `Cmd+Shift+X`).
- Search for `PlatformIO IDE` (Ant face).
- Click **Install** on the official extension by PlatformIO.
	- The installation usually takes a few minutes to download the necessary core files. You might be asked to restart or reload the window once finished.

## Getting Started!
Once everything are prepared.
### Creating a new project
- Open VS Code
- Click the `PlatformIO IDE` icon on the left sidebar.
- There are two ways to create your new project:
	- Project Tasks
		- Click `Create New Project`
		- Click `New Project`
	- Sidebar under Quick Access
		- PIO Home
		- Click `Open`
		- Click `New Project`
- Name
	- Project Name (e.g., Blink_Test)
- Board
	- Adafruit Feather ESP32 V2
- Framework
	- Arduino
- Click `Finish`
### Start writing your code
- Go to **Explorer** (usually you will start from here)
- Open the `src` folder
	- Click `main.cpp` (this will be the main file for you to edit)
- Click [here](Skeleton%20Code.md) to see my code, and then please fill it out to complete the assignment.
### Compile and upload
- Connect your ESP32 to your laptop/computer via USB.
- There are two ways in compile and upload your code:
	- Look at the **Blue Status Bar** at the very bottom of the VS Code window.
	    - `Checkmark` (✓): This is "Build" (Compile). Click it first to ensure there are no errors.
	    - `Right Arrow` (→): This is "Upload".
	    - Click the Right Arrow (→) to upload.
	- Sidebar under:
		- Click the `PlatformIO Icon` (Ant face).
		- Expand Project Tasks > Your Board Name (in this case will be `adafruit_feather_esp32_v2)` > General.
		- Click `Upload`
### Monitor the output
There are two ways to see the output:
- Blue Status Bar
	- Click the `Plug Icon`
- Sidebar under:
	- Click the `PlatformIO Icon`
	- Under Project Tasks
		- Under `General`
			- Click `Monitor`
After you click Monitor, you should see the output that you filled out in the code, and the ESP32 should be blinking.


Note:
- Ensure the baud rate is matched.
### Troubleshooting
If you see an error like `A fatal error occurred: Failed to connect to ESP32: Timed out...`:
- Hold the **BOOT** Button
    - Press and hold the BOOT button on your ESP32 board.
    - Click the **Upload** arrow in VS Code.
    - When you see the text **Connecting...** in the terminal, **release** the BOOT button.
- Check your Cable: Ensure you are not using a "charge-only" cable. Try a different USB cable.
- If you see an output as a strange icon, please check the `monitor_speed`
	- Go to **Explorer**
	- Under `platformoi.ini`
		- If there is no `monitor_speed = XXXXX`, please add it.
		- `XXXXX` needs to match your baud rate in your code
	- If there is no change in the serial monitor, you have to kill the old one first.

### References
- [Adafruit Website](https://learn.adafruit.com/adafruit-esp32-feather-v2/blink)
- [How to setup PlatformIO with VScode](https://www.youtube.com/watch?v=3ATDCi4ApY4)