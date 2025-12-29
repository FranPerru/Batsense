🦇 Batsense - Haptic Tactical Assistance for Table Soccer
Batsense is a real-time computer vision system designed to enhance table soccer. It tracks players, the ball, and goals to provide automated refereeing and immersive haptic feedback via ESP32 microcontrollers.

🚀 Features
Real-time Tracking: High-speed detection of players (Red/Blue), the ball (Cyan), and goals (Yellow/Neon Green) using OpenCV.

Haptic Feedback: Sends proportional vibration alerts to players' wrists/waists via HTTP requests to ESP32 units.

Smart Scoreboard: Automated goal detection with a built-in "cooldown" to prevent double-counting.

Live HUD: On-screen display showing proximity distances, team scores, and system status.

🛠️ Requirements
Hardware

Camera: Standard webcam (mounted top-down).

Processer: PC/Laptop capable of running Python 3.x.

Microcontrollers: 4x ESP32 modules.

Actuators: 4x Vibration motors with MOSFET/Transistor drivers.

Software (Python Dependencies)

Install the required libraries using the included requirements.txt:

Bash
pip install -r requirements.txt
📂 Project Structure
src/: Contains main.py (The core vision and logic engine).

firmware/: Contains esp32_haptic_driver.ino (The code for the vibration units).

requirements.txt: List of necessary Python packages.

🔧 Setup & Installation
WiFi Configuration: Open firmware/esp32_haptic_driver.ino and enter your WiFi credentials:

C++
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
IP Mapping: Once your ESP32s are connected, note their IP addresses and update them in src/main.py:

Python
RED_PLAYER_VIBRATOR_URL = "http://192.168.1.X/red/player"
# ... update all 4 URLs<img width="1470" height="956" alt="Captura de pantalla 2025-11-24 a la(s) 8 09 20 p  m" src="https://github.com/user-attachments/assets/446552d5-f2e4-4381-ad1d-e487ba5fa7ee" />

🎮 How to Use
Power on your ESP32 units and ensure they are on the same network as your PC.

Run the vision system:

Bash
python src/main.py
Controls:

Press 'i': Toggle the Detailed Proximity Panel.

Press 'q': Exit the application.
<img width="1470" height="956" alt="Captura de pantalla 2025-11-24 a la(s) 8 09 20 p  m" src="https://github.com/user-attachments/assets/822efbce-bf6a-4ce6-a4bf-a015dd10f86e" />

