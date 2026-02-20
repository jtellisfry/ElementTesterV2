# Element-Tester
This will be a program for the Frymaster Element Tester to test the high potential and resistance.

## Important Testing Information
- This version of the Element Tester uses the Fluke287 so all the measurement logic is internal unlike Version 1 of the Element Tester
- This version also has the option to switch between the USB-ERB08 relay module or the USB-PDIS08 relay module for better interchangability

## Installing and deploying this program
- Install python version 3.13
- Go to this location in your command prompt or open it in your coding environment (VSCode, etc.) and find it in your File Explorer
  - cd "C:\Files\element tester\Element_Tester"
- When installing on a fresh computer there should NOT be a ".venv" folder at the top and if there is then delete it
  - Reinitialize it with "python -m venv .venv" in the terminal
  - Then you will have to install the requirements.txt file with the command "pip install -r requirements.txt"
- BELOW shows you have to rebuild or do the initial build for the executable version of the program
  - If you want to bring it to the desktop, simply create a shortcut and put it on the desktop, do not remove the main file

## If you are trying to rebuild a new executable file (.exe file) after changing something use this process
- Step 1: Open command prompt or powershell
- Step 2: Run this command --> cd "C:\Files\element tester\Element_Tester"
- Step 3: Activate the virtual environment with these commands in that order and you should see a (.venv) appear in front of the location you cd into -->
  - SetExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  - ".\.venv\Scripts\Activate.ps1"
- Step 4: Run this command --> python build_application.py
  - This should build and overrite the previous version of the application



  
