import socket
import numpy as np
import joblib
import requests
import time
from collections import deque
from datetime import datetime

# --- CONFIGURATION ---
UDP_IP = "0.0.0.0"
UDP_PORT = 4210
MODEL_FILE = "fall_model.pkl"

# --- TELEGRAM CONFIGURATION (FIXED) ---
TELEGRAM_TOKEN = "YOUR TOKEN HERE"
TELEGRAM_CHAT_ID = "YOUR TOKEN HERE"


def send_telegram_notification(confidence):
    """Sends a formatted alert message to the caretaker via Telegram."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = (
        f"🚨 *FALL DETECTED!*\n"
        f"--------------------------\n"
        f"🕒 *Time:* {timestamp}\n"
        f"🎯 *AI Confidence:* {confidence:.1f}%\n"
        f"📍 *Status:* Immediate attention required."
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ Telegram Alert Sent at {timestamp}")
        else:
            print(f"❌ Telegram API Error: {response.text}")
    except Exception as e:
        print(f"❌ Notification Failed: {e}")


# --- INITIALIZATION ---
print("🔄 Loading AI Model...")
try:
    model = joblib.load(MODEL_FILE)
    print("✅ Model Loaded Successfully!")
except Exception as e:
    print(f"❌ Error: {e}")
    exit()

# Buffer for sliding window
buffer = deque(maxlen=200)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

print(f"🚀 Server Listening on Port {UDP_PORT}...")

last_alert_time = 0

while True:
    try:
        # 1. Non-blocking data receive
        try:
            data, addr = sock.recvfrom(1024)
            payload = data.decode('utf-8').split(',')
            if len(payload) == 3:
                ax, ay, az = map(float, payload)
                buffer.append([ax, ay, az])
        except BlockingIOError:
            continue

        # 2. Process when window is full
        if len(buffer) == 200:
            window_array = np.array(buffer)

            # Calculate Total Acceleration Magnitude: sqrt(x^2 + y^2 + z^2)
            magnitudes = np.linalg.norm(window_array, axis=1)
            max_mag = np.max(magnitudes)
            min_mag = np.min(magnitudes)

            # 3. TRIGGER LOGIC
            if max_mag > 2.0 or min_mag < 0.5:

                # Reshape for Scikit-Learn (1 sample, 600 features)
                features = window_array.flatten().reshape(1, -1)

                # Get probabilities
                probs = model.predict_proba(features)[0]
                fall_confidence = probs[1]

                if fall_confidence > 0.50:  # Threshold for testing
                    current_time = time.time()

                    if current_time - last_alert_time > 10:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"⚠️ FALL DETECTED! Confidence: {fall_confidence * 100:.1f}%")

                        # Send feedback to ESP32
                        sock.sendto(b"FALL", addr)

                        # --- NEW NOTIFICATION PART ---
                        send_telegram_notification(fall_confidence * 100)

                        last_alert_time = current_time

                        # Slide forward to avoid double-triggering
                        for _ in range(50): buffer.popleft()

    except Exception as e:

        print(f"Loop Error: {e}")
