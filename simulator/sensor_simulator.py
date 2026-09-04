import random
import time

import requests

API_URL = "http://localhost:8000/api/v1/readings"

DEVICE_ID = 1

print("========================================")
print("QuantPulse Sensor Simulator Started")
print("Sending data every 5 seconds...")
print("Press CTRL+C to stop")
print("========================================")

while True:
    temperature = round(random.uniform(20.0, 45.0), 1)
    humidity = round(random.uniform(10.0, 70.0), 1)
    battery = random.randint(5, 100)

    payload = {
        "device_id": DEVICE_ID,
        "temperature": temperature,
        "humidity": humidity,
        "battery": battery,
    }

    try:
        response = requests.post(
            API_URL,
            json=payload,
            timeout=5,
        )

        print("-" * 50)
        print(f"Temperature : {temperature} °C")
        print(f"Humidity    : {humidity} %")
        print(f"Battery     : {battery} %")
        print(f"Status Code : {response.status_code}")

        if response.status_code != 201:
            print("Response:", response.text)

    except requests.exceptions.RequestException as e:
        print("Connection Error:", e)

    time.sleep(5)