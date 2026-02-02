
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

PORT = int(os.getenv("PORT", 5001))
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "192.168.1.5") 

WEBHOOK_URL = f"http://{WEBHOOK_HOST}:{PORT}/webhook/evolution"

def register_webhook():
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }

    print(f"Connecting to Evolution API at {EVOLUTION_API_URL}...")
    
    try:
        # 1. Fetch Instance
        res = requests.get(f"{EVOLUTION_API_URL}/instance/fetchInstances", headers=headers)
        res.raise_for_status()
        instances = res.json()
        if not instances:
            print("No instances found.")
            return
        
        instance_name = instances[0].get("name")
        print(f"Found Instance: {instance_name}")
        
        # 2. Update Webhook
        print(f"Setting webhook to: {WEBHOOK_URL}")
        
        set_url = f"{EVOLUTION_API_URL}/webhook/set/{instance_name}"
        payload = {
             "webhook": {
                "enabled": True,
                "url": WEBHOOK_URL,
                "webhookByEvents": True,
                "events": [
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE", 
                    "SEND_MESSAGE",
                    "CONNECTION_UPDATE"
                ]
            }
        }
        
        res = requests.post(set_url, headers=headers, json=payload)
        
        if res.status_code == 200:
            print("✅ Webhook updated successfully!")
            print(res.json())
        else:
            print(f"❌ Failed to update webhook: {res.status_code}")
            print(res.text)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    register_webhook()
