import requests
import json
import time

def test_server_text_flow():
    url = "http://localhost:8000/webhook/evolution"
    
    # Payload similar to Evolution API
    payload = {
        "event": "messages.upsert",
        "instance": "instance",
        "data": {
            "key": {
                "remoteJid": "558199999999@s.whatsapp.net"
            },
            "message": {
                "conversation": "Quero saber o valor do exame e se aceita Unimed"
            }
        }
    }
    
    print(f"Sending payload to {url}...")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        data = response.json()
        assert response.status_code == 200
        assert data["status"] == "processed"
        assert data["intent"] == "ORCAMENTO"
        assert data["entities"].get("PLANO_SAUDE") == "ID_UNIMED"
        print("SUCCESS: Text flow matched Intent and Entity.")
        
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    # Wait a bit for server to start if run immediately after
    time.sleep(2) 
    test_server_text_flow()
