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

    def send_text(self, client_id, remote_jid, text):
        """
        Sends a text message to the specified remoteJid via local Node gateway.
        """
        url = f"http://localhost:3000/send-message/{client_id}"
        
        payload = {
            "number": remote_jid,
            "text": text
        }
        
        try:
            response = requests.post(url, json=payload, timeout=20)
            if response.status_code == 200:
                print(f"[REPLIER] [{client_id}] Sent to {remote_jid}: {text}")
            else:
                print(f"[REPLIER] [{client_id}] Gateway Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[REPLIER] [{client_id}] Error sending: {e}")
        

