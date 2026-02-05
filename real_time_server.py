import socket
import numpy as np
import joblib
import requests
import time
from collections import deque
from datetime import datetime  # New import for timestamp

# --- CONFIGURATION ---
UDP_IP = "0.0.0.0"
UDP_PORT = 4210
MODEL_FILE = "fall_model.pkl"

# Blynk Config
BLYNK_AUTH = "lcEfKwsoa_NLCfNmW3KWgomj4AL2f77sdsadp"
BLYNK_URL = f"https://blynk.cloud/external/api/logEvent?token={BLYNK_AUTH}&code=fall_alert"

print("Loading AI Model...")
model = joblib.load(MODEL_FILE)
buffer = deque(maxlen=200)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
print(f"✅ Listening for ESP32 on port {UDP_PORT}...")

last_alert = 0

while True:
    data, addr = sock.recvfrom(1024)
    try:
        parts = data.decode('utf-8').split(',')
        if len(parts) == 3:
            ax = float(parts[0]) / 9.81
            ay = float(parts[1]) / 9.81
            az = float(parts[2]) / 9.81

            buffer.append([ax, ay, az])

            if len(buffer) == 200:
                features = np.array(buffer).flatten().reshape(1, -1)
                pred = model.predict(features)[0]

                if pred == 1:
                    now = time.time()
                    if now - last_alert > 10:
                        # --- CAPTURE TIME ---
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"⚠️ FALL DETECTED at {timestamp}! Source: {addr}")

                        sock.sendto(b"FALL", addr)

                        try:
                            # You can even send the timestamp to Blynk if your event supports it
                            requests.get(BLYNK_URL)
                            print(f" -> Notification Sent at {timestamp}")
                        except:
                            pass

                        last_alert = now
                        buffer.clear()

    except Exception as e:
        print(f"Error: {e}")