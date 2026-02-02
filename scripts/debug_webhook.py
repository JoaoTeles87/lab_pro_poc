
import requests
import json
from src.config import EVOLUTION_API_URL, EVOLUTION_API_KEY, WEBHOOK_URL

def debug_register():
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Fetch instance
    try:
        res = requests.get(f"{EVOLUTION_API_URL}/instance/fetchInstances", headers=headers)
        instance_name = res.json()[0].get("name")
    except:
        print("Failed to get instance")
        return

    set_url = f"{EVOLUTION_API_URL}/webhook/set/{instance_name}"
    
    # Try minimal payload
    payload = {
        "enabled": True,
        "url": WEBHOOK_URL,
        "webhookByEvents": False,
        "events": []
    }
    
    print(f"Sending to {set_url} with payload {json.dumps(payload)}")
    
    res = requests.post(set_url, headers=headers, json=payload)
    
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
    
    with open("debug_webhook_response.txt", "w") as f:
        f.write(res.text)

if __name__ == "__main__":
    debug_register()
