import sys
import os

# Adjust path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.session import SessionManager
from src.core.triage import Triage

def run_scenario(name, phone, messages):
    print(f"\n\n=== SCENARIO: {name} | Phone: {phone} ===")
    
    session_manager = SessionManager()
    # Force clear if possible (or just rely on new phone)
    # session_manager.clear_session(phone) # Not impl, using random phone
    
    triage_service = Triage()
    
    for msg in messages:
        print(f"\n[USER] {msg}")
        
        # 1. Triage
        intent = triage_service.detect_intent(msg)
        entities = triage_service.extract_entities(msg)
        
        # 2. Session Update
        result = session_manager.update_session(
            phone=phone,
            message=msg,
            intent=intent,
            entities=entities,
            contact_name="Test User",
            media_type="text"
        )
        
        if result is None:
            print("[BOT] (SILENCE - Message Ignored)")
        else:
            print(f"[BOT] Status: {result.get('status')}")
            # print(f"[BOT] Action: {result.get('action')}")
            reply = result.get('reply_message')
            if reply:
                print(f"[BOT] >> {reply.replace(chr(10), ' ')}") # Flatten for display
            else:
                print("[BOT] (No Reply)")

def main():
    # Scenario 1: Ignored Messages
    run_scenario("Filters & Ignored Messages", "11111", [
        "...", 
        "abc", # Too short?
        "🥹", 
        "https://google.com",
        "Orçamento" # Should Validly Reply
    ])

    # Scenario 2: Name Logic - Greeting (Should Ask)
    run_scenario("Greeting -> Ask Name -> Name", "22222", [
        "Oi", 
        "Joao Teles"
    ])

    # Scenario 3: Name Logic - Sentence Response (Should Skip Name)
    run_scenario("Greeting -> Ask Name -> Sentence Override", "33333", [
        "Oi", 
        "Tem como marcar um exame de sangue?"
    ])

if __name__ == "__main__":
    main()
