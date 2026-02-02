import re
from unidecode import unidecode

ONTOLOGY = {
    "intents": {
        "ORCAMENTO": ["preco", "valor", "quanto custa", "orcamento", "tabela", "1", "um"],
        "RESULTADO": ["resultado", "laudo", "ja saiu", "exame pronto", "protocolo", "2", "dois"],
        "AGENDAMENTO": ["marcar", "agendar", "domiciliar", "coleta", "3", "tres"],
        "TOXICOLOGICO": ["toxicologico", "4", "quatro"]
    },
    "entities": {
        "PLANO_SAUDE": {
            "ID_UNIMED": ["unimed", "uni med", "unimeid", "unimed recife"],
            "ID_BRADESCO": ["bradesco", "bradesco saude", "bradesco seguro", "bradoesco", "bardesco", "bra underground"],
            "ID_PARTICULAR": ["dinheiro", "pix", "sem plano", "a vista", "nao tenho plano", "cartao"], #MUDAR PARA PAGAMENTO EM ESPÉCIE SEM PLANO, POIS PARTICULAR GERA CERTA AMBIGUIDADE
            "ID_SASSEPE": ["sassepe", "sassep", "sasepe"],
            "ID_GEAP": ["geap", "jeap", "geape"]
        }
    }
}

def normalize_text(text: str) -> str:
    """
    Normalizes text for regex matching:
    1. Fix Unicode/Accents (unidecode).
    2. Remove URLs (http/https/www).
    3. Normalize repeated characters (elongation).
    4. Remove non-alphanumeric characters (except spaces).
    5. Collapse multiple spaces.
    """
    if not text:
        return ""
    
    # 1. Remove accents and lowercase
    text = unidecode(text).lower()
    
    # 2. Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    
    # 3. Fix Elongated Words (e.g., "bombooomm" -> "bom")
    # Reduces words with 3+ repeated characters to 1
    text = re.sub(r"(.)\1{2,}", r"\1", text)

    # 4. Keep only letters, numbers, spaces
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # 5. Collapse whitespace
    return " ".join(text.split())

class Triage:
    def __init__(self):
        self.ontology = ONTOLOGY
    
    def detect_intent(self, text: str) -> str:
        """
        Detects the intent of the message based on keywords.
        Returns the first matching intent key or None.
        """
        normalized_text = normalize_text(text)
        
        for intent, keywords in self.ontology["intents"].items():
            for keyword in keywords:
                # Simple containment check for now
                if normalize_text(keyword) in normalized_text:
                    return intent
        return None

    def extract_entities(self, text: str) -> dict:
        """
        Extracts entities like Health Plans.
        Returns a dictionary of found entities.
        """
        normalized_text = normalize_text(text)
        found_entities = {}
        
        for entity_type, mapping in self.ontology["entities"].items():
            for entity_id, keywords in mapping.items():
                for keyword in keywords:
                    if normalize_text(keyword) in normalized_text:
                        found_entities[entity_type] = entity_id
                        # Optimization: Break inner loop if specific ID found? 
                        # For now, let's allow finding multiple if they exist, but overwrite for same type.
        return found_entities
