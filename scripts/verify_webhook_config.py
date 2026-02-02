
import requests
from src.config import EVOLUTION_API_URL, EVOLUTION_API_KEY

def check_webhook():
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        # Get instance
        res = requests.get(f"{EVOLUTION_API_URL}/instance/fetchInstances", headers=headers)
        instances = res.json()
        if not instances:
            print("No instances.")
            return
        instance_name = instances[0].get("name")
        print(f"Instance: {instance_name}")
        
        # Get settings/webhook info
        res = requests.get(f"{EVOLUTION_API_URL}/webhook/find/{instance_name}", headers=headers)
        print("Current Webhook Config on Server:")
        print(res.text)
        
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_webhook()
