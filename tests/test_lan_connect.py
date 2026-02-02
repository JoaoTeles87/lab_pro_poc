import requests
import json

URL = "http://192.168.1.11:8000/webhook/evolution"

def test_connectivity():
    print(f"Testing connectivity to {URL}...")
    try:
        # Simple health check payload (Evolution style)
        payload = {
            "event": "messages.upsert",
            "instance": "TEST",
            "data": {
                "key": {"remoteJid": "TEST@s.whatsapp.net"},
                "message": {"conversation": "PING"}
            }
        }
        res = requests.post(URL, json=payload, timeout=5)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"FAILED to connect: {e}")

if __name__ == "__main__":
    test_connectivity()
