import socket
import numpy as np
import joblib
import requests
import time
from collections import deque
from datetime import datetime

# --- CONFIGURATION ---
UDP_IP = "0.0.0.0"  # Listens on all available network interfaces
UDP_PORT = 4210  # Must match the port in your Arduino code
MODEL_FILE = "fall_model.pkl"

# Blynk Config (Update token if you changed it)
BLYNK_AUTH = "lcEfKwsoa_NLCfNmW3KWgomj4AL2f77sdsadp"
BLYNK_URL = f"https://blynk.cloud/external/api/logEvent?token={BLYNK_AUTH}&code=fall_alert"

# --- INITIALIZATION ---
print("🔄 Loading AI Model...")
try:
    model = joblib.load(MODEL_FILE)
    print("✅ Model Loaded Successfully!")
except:
    print("❌ Error: fall_model.pkl not found! Please train the model first.")
    exit()

# Buffer to store the sliding window of 200 samples (3-4 seconds of data)
buffer = deque(maxlen=200)

# Setup UDP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
print(f"🚀 Server Listening on Port {UDP_PORT}...")

last_alert_time = 0

while True:
    # Receive data from ESP32
    data, addr = sock.recvfrom(1024)

    try:
        # Decode the CSV string: "ax,ay,az"
        payload = data.decode('utf-8').split(',')
        if len(payload) == 3:
            ax = float(payload[0])
            ay = float(payload[1])
            az = float(payload[2])

            # Add new data to the sliding window
            buffer.append([ax, ay, az])

            # Wait until we have enough data to make a prediction
            if len(buffer) == 200:
                # 1. CALCULATE WINDOW MAGNITUDE
                # This checks if there was ANY significant movement in the last 200 samples
                window_array = np.array(buffer)
                magnitudes = np.sqrt(np.sum(window_array ** 2, axis=1))
                max_mag = np.max(magnitudes)
                min_mag = np.min(magnitudes)

                # 2. THE MAGNITUDE GATE
                # If the max force was > 1.5g or min force < 0.6g (freefall), then check AI
                # Otherwise, it's just normal standing/sitting stillness.
                if max_mag > 1.5 or min_mag < 0.6:

                    # Flatten the 2D window (200, 3) into a 1D vector (600,) for the model
                    features = window_array.flatten().reshape(1, -1)

                    # 3. PROBABILITY THRESHOLD
                    # Get the confidence levels: [Prob_NoFall, Prob_Fall]
                    probs = model.predict_proba(features)[0]
                    fall_confidence = probs[1]

                    # Only trigger if the AI is more than 85% sure it's a fall
                    if fall_confidence > 0.85:
                        current_time = time.time()

                        # Cooldown: Don't spam alerts (wait 10 seconds between notifications)
                        if current_time - last_alert_time > 10:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f"⚠️ FALL DETECTED! Confidence: {fall_confidence * 100:.1f}% at {timestamp}")

                            # A. Send signal back to ESP32 to light up LED
                            sock.sendto(b"FALL", addr)

                            # B. Send Push Notification via Blynk
                            try:
                                requests.get(BLYNK_URL, timeout=2)
                                print(f" -> Blynk Notification Sent!")
                            except Exception as blynk_err:
                                print(f" -> Blynk Error: {blynk_err}")

                            last_alert_time = current_time
                            buffer.clear()  # Clear buffer after alert to reset the window
                else:
                    # Optional: Print "Status: Still" every few seconds if you want to see it working
                    pass

    except Exception as e:
        print(f"Data Error: {e}")