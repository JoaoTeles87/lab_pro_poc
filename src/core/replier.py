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
            requests.post(url, json=payload)
            print(f"[REPLIER] Sent to {remote_jid}: {text}")
        except Exception as e:
            print(f"[REPLIER] Error sending: {e}")
        

