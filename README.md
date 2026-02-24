# Element-Tester
This will be a program for the Frymaster Element Tester to test the high potential and resistance.

## Important Testing Information
- This version of the Element Tester uses the Fluke287 so all the measurement logic is internal unlike Version 1 of the Element Tester
- This version also has the option to switch between the USB-ERB08 relay module or the USB-PDIS08 relay module for better interchangability

## Installing and deploying this program
- Install python version 3.13
- Go to this location (L:\Test Engineering\Tester Information\ElementTesterV2(Python)) and move the files in the dist folder (under the proper Element Tester version) into the main folder
  - The folder structure on the local machine should be
    - ElementTesterV2
      - main (folder)
      - backup (folder)
      - data (folder)
- Make sure anything involving a com port is configured correctly
  - Hypot3865 = COM 6
  - Fluke287 = COM 11
## If you are trying to rebuild a new executable file (.exe file) after changing something in the code use this process
- Step 1: Create the next version in the "backup" folder on the local machine
- Step 2: Move the current version from "main" into this new "backup" folder location
- Step 3: Go into a powershell terminal and cd into this location "L:\Test Engineering\Tester Information\ElementTesterV2(Python)\ElementTesterV2"
- Step 4: Enter in these prompts in the terminal
  - Prompt 1: set-executionpolicy -scope process -executionpolicy bypass
  - Prompt 2: .\.venv\scripts\activate.ps1
  - Prompt 3: python build_application.py
- Step 5: Move all of the newly created files inside the "dist" folder in the location previously mentioned into the "main" folder on the local machine
  - If you don't move all the files and folders inside the "dist" folder then the program will not work on the local machine



  
