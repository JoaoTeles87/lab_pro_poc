import sys
import os

# Adjust path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.session import SessionManager
from src.core.triage import Triage

def main():
    print("=== WhatsApp Bot Logic Simulator ===")
    print("Type your message to interact with the bot.")
    print("Special commands:")
    print("  /phone <number>  : Switch phone number (default: 12345)")
    print("  /clear           : Clear session for current phone")
    print("  /quit            : Exit")
    
    session_manager = SessionManager()
    triage_service = Triage()
    
    phone = "12345"
    
    while True:
        try:
            user_input = input(f"\n[{phone}] You: ")
        except EOFError:
            break
            
        if user_input.strip() == "/quit":
            break
            
        if user_input.startswith("/phone"):
            parts = user_input.split()
            if len(parts) > 1:
                phone = parts[1]
                print(f"Switched to phone: {phone}")
            else:
                print("Usage: /phone <number>")
            continue

        if user_input.strip() == "/clear":
            # Manually clear session for test (hacky but works for sqlite if we just delete row or ignore)
            # Since we can't easily delete via manager, let's just use a new number or ignore
            print("Session clearing not fully implemented in simulator, try changing number.")
            continue
            
        # Simulate processing
        # 1. Triage
        intent = triage_service.detect_intent(user_input)
        entities = triage_service.extract_entities(user_input)
        
        print(f"[DEBUG] Intent: {intent} | Entities: {entities}")
        
        # 2. Session Update
        result = session_manager.update_session(
            phone=phone,
            message=user_input,
            intent=intent,
            entities=entities,
            contact_name="Test User",
            media_type="text"
        )
        
        if result is None:
            print("[BOT] (Ignored / No Reply)")
        else:
            print(f"[BOT] Status: {result.get('status')}")
            print(f"[BOT] Action: {result.get('action')}")
            print(f"[BOT] Reply: \n{result.get('reply_message')}")

if __name__ == "__main__":
    main()
