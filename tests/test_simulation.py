import requests
import json
import time

URL = "http://localhost:8000/webhook/evolution"

def send_message(phone, message):
    payload = {
        "event": "messages.upsert",
        "instance": "instance",
        "data": {
            "key": {
                "remoteJid": f"{phone}@s.whatsapp.net"
            },
            "message": {
                "conversation": message
            }
        }
    }
    try:
        requests.post(URL, json=payload)
        print(f"Sent: '{message}' from {phone}")
    except Exception as e:
        print(f"Error sending message: {e}")

def test_simulation():
    # User 1: Budget request without plan (Should go to TRIAGEM)
    send_message("558190000001", "Quanto custa um hemograma completo?")
    
    time.sleep(1)
    
    # User 2: Budget request WITH plan (Should go to HUMAN)
    send_message("558190000002", "Quero orçamento de glicose, tenho Unimed")

    time.sleep(1)

    # User 3: Result request (Should go to HUMAN)
    send_message("558190000003", "Meu resultado saiu?")

    # User 1 Again: Provides Plan (Should update to HUMAN)
    time.sleep(2)
    send_message("558190000001", "Ah, esqueci de falar, é pelo Bradesco")

if __name__ == "__main__":
    time.sleep(2) # Wait for server
    test_simulation()
