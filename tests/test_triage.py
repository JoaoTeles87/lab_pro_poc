import sys
import os
sys.path.append(os.getcwd()) # Ensure src is in path

from src.core.triage import Triage, normalize_text

def test_normalization():
    assert normalize_text("Olá Água") == "ola agua"
    assert normalize_text("TESTE   123") == "teste 123"
    assert normalize_text("Quero um orçamento!") == "quero um orcamento"

def test_intent_detection():
    triage = Triage()
    
    # ORCAMENTO
    assert triage.detect_intent("Gostaria de saber o valor do exame") == "ORCAMENTO"
    assert triage.detect_intent("Quanto custa um hemograma?") == "ORCAMENTO"
    assert triage.detect_intent("Preço da glicose") == "ORCAMENTO"
    
    # RESULTADO
    assert triage.detect_intent("Meu resultado ja saiu?") == "RESULTADO"
    assert triage.detect_intent("Quero meu laudo") == "RESULTADO"
    
    # UNKNOWN
    assert triage.detect_intent("Bom dia") is None

def test_entity_extraction():
    triage = Triage()
    
    # UNIMED
    entities = triage.extract_entities("Tenho plano Unimed")
    assert entities.get("PLANO_SAUDE") == "ID_UNIMED"
    
    # BRADESCO
    entities = triage.extract_entities("É pelo bradesco saude")
    assert entities.get("PLANO_SAUDE") == "ID_BRADESCO"
    
    # PARTICULAR
    entities = triage.extract_entities("Vou pagar no particular")
    assert entities.get("PLANO_SAUDE") == "ID_PARTICULAR"
    
    # None
    entities = triage.extract_entities("Não sei qual é")
    assert "PLANO_SAUDE" not in entities

if __name__ == "__main__":
    try:
        test_normalization()
        print("test_normalization: PASS")
        test_intent_detection()
        print("test_intent_detection: PASS")
        test_entity_extraction()
        print("test_entity_extraction: PASS")
    except AssertionError as e:
        print(f"FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1)
