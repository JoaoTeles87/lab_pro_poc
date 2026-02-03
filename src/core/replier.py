import requests
import json
import urllib.parse

from src.config import EVOLUTION_API_URL, EVOLUTION_API_KEY

class Replier:
    def __init__(self):
        self.headers = {
            "apikey": EVOLUTION_API_KEY,
            "Content-Type": "application/json"
        }

    def send_text(self, remote_jid, text):
        """
        Sends a text message to the specified remoteJid via local Node gateway.
        """
        url = "http://localhost:3000/send-message"
        
        payload = {
            "number": remote_jid,
            "text": text
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"[REPLIER] Sent to {remote_jid}: {text}")
            else:
                print(f"[REPLIER] Gateway Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[REPLIER] Error sending: {e}")
        

