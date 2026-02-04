import sys
import os
from fastapi.testclient import TestClient

# Adjust path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.webhook import app

client = TestClient(app)

def test_webhook_ignored_messages():
    print("\n--- Testing Ignored Messages ---")
    
    # 1. Emoji only
    payload = {
        "remoteJid": "12345@s.whatsapp.net",
        "text": "🥹",
        "mediaType": "text"
    }
    response = client.post("/webhook", json=payload)
    print(f"CASE: Emoji -> Status: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    assert response.json().get("status") == "ignored"

    # 2. Empty string
    payload["text"] = ""
    response = client.post("/webhook", json=payload)
    print(f"CASE: Empty Text -> Status: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    assert response.json().get("status") == "ignored"

    # 3. Link only
    payload["text"] = "https://google.com"
    response = client.post("/webhook", json=payload)
    print(f"CASE: Link Only -> Status: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    assert response.json().get("status") == "ignored"

def test_webhook_valid_message():
    print("\n--- Testing Valid Messages ---")
    payload = {
        "remoteJid": "12345@s.whatsapp.net",
        "text": "Orçamento",
        "mediaType": "text"
    }
    response = client.post("/webhook", json=payload)
    print(f"CASE: 'Orçamento' -> Status: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    assert response.json().get("status") == "processed"

if __name__ == "__main__":
    try:
        test_webhook_ignored_messages()
        test_webhook_valid_message()
        print("\n✅ API Layer Verification PASSED")
    except AssertionError as e:
        print(f"\n❌ API Layer Verification FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ API Layer Verification CRASHED: {e}")
        exit(1)
