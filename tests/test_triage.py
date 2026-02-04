import sys
import os

# Adjust path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.triage import Triage

def test_triage():
    triage = Triage()
    
    test_cases = [
        # 1. False Positive Correction (The "Mim ama" case)
        ("Mim ama ou mim odeia fica a critério n como as custas de nenhum", None),
        ("Eu não tenho nenhum centavo", None), # 'um' inside 'nenhum'
        ("Vou comp um carro", None), # 'um' inside 'compum' (artificially) or just 'um' is gone?
                                     # We removed 'um' entirely from ontology.
        
        # 2. Valid Intents (Strict Digits)
        ("1", "ORCAMENTO"),
        ("1.", "ORCAMENTO"),
        ("Opção 1", "ORCAMENTO"),
        ("Quero saber o preco", "ORCAMENTO"),
        
        # 3. Invalid Digits (Boundaries)
        ("100 reais", None), # Should NOT trigger '1'
        ("2024", None),      # Should NOT trigger '2' or '4'
        ("30", None),
        
        # 4. Links (Should be stripped by normalizer implicitly)
        ("https://www.instagram.com/p/DURsQsWADan/?igsh=MWttZGM5ZmMwbzR2YQ==", None),
        
        # 5. Other Intents
        ("resultado", "RESULTADO"),
        ("agendar", "AGENDAMENTO"),
        ("toxicologico", "TOXICOLOGICO"),
    ]
    
    print("\n=== TRIAGE LOGIC VERIFICATION ===")
    failures = 0
    for text, expected in test_cases:
        result = triage.detect_intent(text)
        status = "✅ PASS" if result == expected else f"❌ FAIL (Got {result})"
        print(f"Input: '{text}' -> Expected: {expected} | {status}")
        if result != expected:
            failures += 1
            
    if failures == 0:
        print("\n🎉 ALL TESTS PASSED")
    else:
        print(f"\n⚠️ {failures} TESTS FAILED")
        exit(1)

if __name__ == "__main__":
    test_triage()
