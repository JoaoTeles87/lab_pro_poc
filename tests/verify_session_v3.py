import sys
import os
import time
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.getcwd())

from src.core.session import SessionManager
from src.core import database

def test_session_v3():
    print("🚀 Starting Session V3 Final Verification...")
    
    # Setup
    os.makedirs("data", exist_ok=True)
    sm = SessionManager()
    client_id = "test_clinic"
    phone = "5511999999999"
    
    # Reset any existing session
    session = sm.get_session(client_id, phone)
    session["status"] = "MENU_PRINCIPAL"
    session["data"] = {}
    session["last_updated"] = time.time()
    database.save_session(client_id, phone, session)

    # 1. Test Option 5 Handoff
    print("\n[TEST 1] Option 5 Handoff")
    res = sm.update_session(client_id, phone, "5", "NONE", {})
    assert res["status"] == "AGUARDANDO_HUMANO"
    assert "atendentes" in res["reply_message"]
    print("✅ Option 5 correctly transitions to AGUARDANDO_HUMANO")
    
    # 2. Test 2h Timeout from Human -> Silent Reset
    print("\n[TEST 2] 2h Timeout from Human -> Silent Reset")
    session = database.get_session(client_id, phone)
    # Simulate 2h 5m ago
    session["last_updated"] = time.time() - (7200 + 300) 
    database.save_session(client_id, phone, session)
    
    # User sends a message that bot doesn't understand (e.g. "Obrigado!")
    res = sm.update_session(client_id, phone, "Obrigado!", None, {})
    
    # Should be SILENT and reset to MENU_PRINCIPAL internally if it was stale human
    assert res is None
    session_after = database.get_session(client_id, phone)
    assert session_after["status"] == "MENU_PRINCIPAL"
    assert "was_stale_human" not in session_after["data"]
    print("✅ Intelligent Silent Reset working: Stale human session remained silent on unknown msg.")
    
    # 3. Test Greeting after Stale Human -> Menu
    print("\n[TEST 3] Greeting after Stale Human -> Menu")
    # Reset to stale human state again
    session_after["status"] = "AGUARDANDO_HUMANO"
    session_after["last_updated"] = time.time() - (7200 + 300)
    database.save_session(client_id, phone, session_after)
    
    # Use says "Oi"
    res = sm.update_session(client_id, phone, "Oi", "GREETING", {})
    assert res["status"] == "MENU_PRINCIPAL"
    # Case-insensitive check for menu content
    assert "orçamentos" in res["reply_message"].lower()
    print("✅ Bot responds with Menu on Greeting even if previously in stale human state.")
    
    # 4. Test Intent after Stale Human -> Flow
    print("\n[TEST 4] Intent after Stale Human -> Flow")
    # Reset to stale human state again
    session = database.get_session(client_id, phone)
    session["status"] = "AGUARDANDO_HUMANO"
    session["last_updated"] = time.time() - (7200 + 300)
    database.save_session(client_id, phone, session)
    
    # User says "Quero um orçamento" (Intent: ORCAMENTO)
    res = sm.update_session(client_id, phone, "Quero um orçamento", "ORCAMENTO", {})
    assert res["status"] == "ORCAMENTO_PEDIR_PLANO"
    print("✅ Bot processes Intent correctly even if previously in stale human state.")
    
    # 5. Test Reset during AGUARDANDO_HUMANO (Active)
    print("\n[TEST 5] Manual Reset in AGUARDANDO_HUMANO")
    session["status"] = "AGUARDANDO_HUMANO"
    session["last_updated"] = time.time() # Recent
    database.save_session(client_id, phone, session)
    
    # User sends "1" (Explicit Reset)
    res = sm.update_session(client_id, phone, "1", "ORCAMENTO", {})
    assert res["status"] == "ORCAMENTO_PEDIR_PLANO"
    print("✅ Manual reset (Option 1-5) works even if human mode is active (New fix).")

    print("\n✨ All Final Session V3 tests passed!")

if __name__ == "__main__":
    test_session_v3()
