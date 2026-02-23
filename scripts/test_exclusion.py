from src.core.session import SessionManager
from src.config import IGNORED_NUMBERS, TEST_PREFIX

def test_exclusions():
    manager = SessionManager()
    ignored_phone = IGNORED_NUMBERS[0] if IGNORED_NUMBERS else "5587999497007"
    regular_phone = "5587000000000"
    
    print(f"--- TESTING WITH IGNORED NUMBER: {ignored_phone} ---")
    
    # 1. Normal message from ignored number
    res = manager.update_session(ignored_phone, "Oi", None, {})
    print(f"Normal message result: {res} (Expected: None)")
    
    # 2. Test mode message from ignored number
    res = manager.update_session(ignored_phone, f"{TEST_PREFIX} Oi", None, {})
    print(f"Test mode result: {'SUCCESS' if res and res.get('reply_message') else 'FAILURE'}")
    if res:
        print(f"Reply: {res.get('reply_message')[:50]}...")

    # 3. Bare prefix from ignored number
    res = manager.update_session(ignored_phone, TEST_PREFIX, None, {})
    print(f"Bare prefix result: {'SUCCESS' if res and res.get('reply_message') else 'FAILURE'}")

    print(f"\n--- TESTING WITH REGULAR NUMBER: {regular_phone} ---")
    
    # 4. Normal message from regular number
    res = manager.update_session(regular_phone, "Oi", None, {})
    print(f"Regular message result: {'SUCCESS' if res and res.get('reply_message') else 'FAILURE'}")

if __name__ == "__main__":
    test_exclusions()
