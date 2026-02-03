import json
import os
import time
from datetime import datetime
from src.core import database

SESSION_FILE = os.path.join("data", "sessions.json")
MOCK_DB_FILE = os.path.join("data", "mock_db.json")
SESSION_TIMEOUT = 300 # 5 minutes (Testing Mode)

class SessionManager:
    def __init__(self):
        # Initialize DB on startup
        database.init_db()
        # Auto-maintenance: Prune old sesions (>120 days / 4 months)
        database.prune_old_sessions(120)
        
        # Mock DB for results lookup (read-only json)
        self.mock_db_path = MOCK_DB_FILE
        self._load_mock_db()

    def get_session(self, phone: str) -> dict:
        """Loads session from DB or creates new."""
        session = database.get_session(phone)
        if not session:
             session = {
                "phone": phone,
                "status": "MENU_PRINCIPAL",
                "data": {},
                "history": [],
                "last_updated": 0,
                "interaction_count": 0,
                "last_action": None
            }
        return session

    def _load_mock_db(self):
        if os.path.exists(self.mock_db_path):
             with open(self.mock_db_path, "r", encoding='utf-8') as f:
                 self.mock_db = json.load(f)
        else:
            self.mock_db = {"patients": {}}

    def check_results(self, protocol_or_cpf):
        # Implement Logic to check Mock DB
        patients = self.mock_db.get("patients", {})
        
        # Simple search
        if protocol_or_cpf in patients:
            patient = patients[protocol_or_cpf]
            results = []
            for exam in patient["exams"]:
                status_icon = "✅" if exam["status"] == "PRONTO" else "🕒"
                results.append(f"{status_icon} *{exam['name']}*: {exam['status']}")
            
            if not results:
                return f"Olá *{patient['name']}*. Ainda não há exames prontos neste protocolo."
                
            return f"Resultados para *{patient['name']}*:\n" + "\n".join(results)
        
        return None

    def update_session(self, phone: str, message: str, intent: str, entities: dict, contact_name: str = None, media_type: str = "text"):
        session = self.get_session(phone)
        
        # Increment Interaction Count (new conversations)
        if intent == "GREETING" or session["interaction_count"] == 0:
            session["interaction_count"] += 1

        # --- NAME REGISTRATION Logic ---
        # 1. If we don't have a name yet
        if not session["data"].get("name"):
            # 2. Try to use contact_name if valid (not just a phone number)
            # Simple heuristic: if contact_name has letters and is not None
            if contact_name and any(c.isalpha() for c in contact_name):
                 session["data"]["name"] = contact_name
                 # Continue to Menu...
            
            # 3. If still no name, and we are not in 'CADASTRO' state, INTERRUPT FLOW
            elif session["status"] != "CADASTRO_PEDIR_NOME":
                 session["status"] = "CADASTRO_PEDIR_NOME"
                 # Save session and return immediately
                 # We need to handle the Reply at the end, so we set a flag or handle logic below
        
        # --- TIMEOUT CHECK ---
        # If last update was > SESSION_TIMEOUT, auto-reset to MENU
        now = time.time()
        last_ts = session.get("last_updated", 0)
        
        if last_ts > 0 and (now - last_ts) > SESSION_TIMEOUT:
             print(f"[SESSION] Timeout detected for {phone}. Resetting to MENU.")
             # Preserve name before clearing data
             saved_name = session["data"].get("name")
             
             session["status"] = "MENU_PRINCIPAL"
             session["data"] = {}
             
             if saved_name: 
                 session["data"]["name"] = saved_name
             
             session["interaction_count"] += 1 # New interaction flow


        session["history"].append({
            "timestamp": now,
            "role": "user",
            "message": message,
            "intent": intent
        })

        # --- STATE MACHINE ---
        
        reply_action = None
        reply_message = None
        
        # Current State
        current_status = session.get("status", "MENU_PRINCIPAL")
        
        # RESET logic (if user says "oi", "ola", "menu" intentionally)
        # Note: if users says "oi" inside a flow, we might want to reset or ignore.
        # For this POC, strong reset on specific keywords helps navigation.
        # RESET logic (if user says "oi", "ola", "menu" intentionally)
        # Note: We EXCLUDE 'AGUARDANDO_HUMANO' from this logic to respect the strict timeline/silence requested.
        is_reset_input = (intent == "GREETING" or 
                          any(x in normalize_text_simple(message) for x in ["oi", "ola", "comecar", "menu", "inicio"]) or 
                          message.strip() in ["1", "2", "3", "4"])
        
        if is_reset_input and current_status != "AGUARDANDO_HUMANO":
             current_status = "MENU_PRINCIPAL"
             # Clear data but preserve Name
             saved_name = session["data"].get("name")
             session["data"] = {} 
             if saved_name: session["data"]["name"] = saved_name

        # LOGIC
        if current_status == "MENU_PRINCIPAL":
            # 0. Global Audio Handoff Rule
            # Audio messages in the main menu often contain complex requests.
            # We skip bot logic and send directly to human.
            if media_type == "audio":
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "HANDOFF_AUDIO"
                 reply_message = "Recebi seu áudio! 🎧\nComo áudios podem conter detalhes importantes, transferi para nossa equipe ouvir com atenção. Aguarde um momento. ⏳"
            
            # Explicit Greeting Re-handling (to avoid "Sorry i didn't understand" for "Oi")
            elif intent == "GREETING" or any(x in normalize_text_simple(message) for x in ["oi", "ola", "comecar", "inicio"]):
                 reply_action = "SEND_MENU"
                 name_display = session["data"].get("name", "Cliente")
                 reply_message = (f"Olá novamente, *{name_display}*! 👋\n"
                                  "1. Solicitação de orçamentos 💰\n"
                                  "2. Solicitação de resultados 🧪\n"
                                  "3. Agendamento domiciliar 📆\n"
                                  "4. Toxicologico")
            
            # Smart Inference: If user mentions a Plan directly (e.g. "Bradesco"), assume ORCAMENTO
            elif entities.get("PLANO_SAUDE"):
                plan = entities["PLANO_SAUDE"]
                session["data"]["plano"] = plan
                session["status"] = "ORCAMENTO_PEDIR_PEDIDO"
                reply_action = "ASK_ORDER"
                reply_message = f"Entendi, plano {plan}. 🏥\nPara orçamentos, por favor envie uma **foto do pedido médico** 📸 ou digite os exames."
            
            elif intent == "ORCAMENTO":
                session["status"] = "ORCAMENTO_PEDIR_PLANO"
                reply_action = "ASK_PLAN"
                reply_message = "Certo, Orçamentos. 💰\nVocê possui plano de saúde ou pagamento **à vista/sem plano**?\n(Ex: Unimed, Bradesco, Sem plano)"
            
            elif intent == "RESULTADO":
                session["status"] = "RESULTADO_PEDIR_COMPROVANTE"
                reply_action = "ASK_PROOF"
                reply_message = "Para verificar seus resultados 🧪, por favor envie a **foto do comprovante** de pagamento/atendimento. 📸"
            
            elif intent == "AGENDAMENTO":
                session["status"] = "AGENDAMENTO_PEDIR_DADOS"
                reply_action = "ASK_ADDR"
                reply_message = "Agendamento Domiciliar 🏠.\nPor favor, digite seu **Endereço Completo**."
                
            elif intent == "TOXICOLOGICO":
                reply_action = "INFO_TOXIC"
                reply_message = "O exame Toxicológico 🚦 é realizado por ordem de chegada.\nNecessário CNH. Valor: R$ 130,00."
                session["status"] = "MENU_PRINCIPAL" # Return to menu
            
            else:
                # Smart Menu Loop Prevention
                last_act = session.get("last_action")
                
                # 1. Long Message / Complexity Handoff
                # If message is long (> 60 chars) and no intent found, assume complex query -> Human
                if len(message) > 60:
                        session["status"] = "AGUARDANDO_HUMANO"
                        reply_action = "HANDOFF_COMPLEX"
                        reply_message = "Estou transferindo para um de nossos atendentes analisarem sua mensagem. Aguarde um momento. ⏳"
                    
                # 2. Loop Prevention
                elif last_act in ["SEND_MENU", "WELCOME", "SENT_SHORT_MENU"]:
                        reply_action = "SENT_SHORT_MENU"
                        reply_message = ("Desculpe, não entendi. 😕\nPoderia repetir ou digitar o número?\n\n"
                                        "1. Orçamentos\n"
                                        "2. Resultados\n"
                                        "3. Agendamento\n"
                                        "4. Toxicológico")
                else:
                    # Default Menu (Long Version)
                    reply_action = "SEND_MENU"
                    # Safe Access to Name
                    name_display = session["data"].get("name", "Cliente")
                    reply_message = (f"Laboratório Pró-Análise agradece o seu contato, *{name_display}*! ✅\n\n"
                                        "Em que posso te ajudar hoje?😄\n"
                                        "Esta é uma mensagem automática em breve você será atendido 😉\n\n"
                                        "1. Solicitação de orçamentos:💰\n"
                                        "Necessário a requisição médica, caso tenha.\n"
                                        "Informar se possui algum plano de saúde\n\n"
                                        "2. Solicitação de resultados de exames: 🧪\n"
                                        "Necessário envio do COMPROVANTE\n\n"
                                        "3. Agendamento de coletas domiciliares: 📆\n"
                                        "Informar os exames e Endereço\n\n"
                                        "4. Toxicologico")

        elif current_status == "CADASTRO_PEDIR_NOME":
            # Capture Name
            clean_name = message.strip()
            
            # Sanity Check: If message is too long (> 50 chars), it's likely a question/audio, not a name.
            if len(clean_name) > 50:
                 # Don't set name to "Cliente", leave it empty so it can be updated by contact sync later.
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "HANDOFF_LONG_REG"
                 reply_message = "Recebi sua mensagem! 🎧\nComo não entendi seu nome, encaminhei direto para nossa equipe humana. Aguarde um momento. 😉"
            
            elif len(clean_name) > 2:
                session["data"]["name"] = clean_name
                session["status"] = "MENU_PRINCIPAL"
                reply_action = "WELCOME"
                reply_message = (f"Obrigado, *{clean_name}*! Prazer em te conhecer. ✨\n\n"
                                 "Em que posso te ajudar hoje?😄\n"
                                     "Esta é uma mensagem automática em breve você será atendido 😉\n\n"
                                     "1. Solicitação de orçamentos:💰\n"
                                     "Necessário a requisição médica, caso tenha.\n"
                                     "Informar se possui algum plano de saúde\n\n"
                                     "2. Solicitação de resultados de exames: 🧪\n"
                                     "Necessário envio do COMPROVANTE\n\n"
                                     "3. Agendamento de coletas domiciliares: 📆\n"
                                     "Informar os exames e Endereço\n\n"
                                     "4. Toxicologico")
            else:
                reply_message = "Nome muito curto. Por favor, digite seu nome completo."

        elif current_status == "ORCAMENTO_PEDIR_PLANO":
            # Capture Plan
            plan = entities.get("PLANO_SAUDE")
            if plan:
                session["data"]["plano"] = plan
                session["status"] = "ORCAMENTO_PEDIR_PEDIDO"
                reply_action = "ASK_ORDER"
                reply_message = f"Ok, plano {plan}. Agora, por favor envie uma **foto do pedido médico** 📸 ou digite os exames."
            else:
                # Try simple key word extraction from message if entity failed
                msg_lower = message.lower()
                if "particular" in msg_lower:
                    session["data"]["plano"] = "PARTICULAR"
                    session["status"] = "ORCAMENTO_PEDIR_PEDIDO"
                    reply_action = "ASK_ORDER"
                    reply_message = "Certo, Particular. Por favor envie uma **foto do pedido médico** 📸 ou digite os exames."
                elif "unimed" in msg_lower:
                    session["data"]["plano"] = "UNIMED"
                    session["status"] = "ORCAMENTO_PEDIR_PEDIDO"
                    reply_action = "ASK_ORDER"
                    reply_message = "Certo, Unimed. Por favor envie uma **foto do pedido médico** 📸 ou digite os exames."
                else:
                    reply_message = "Não entendi qual é o plano. Aceitamos Unimed, Bradesco, Sassepe, Geap ou Particular."

        elif current_status == "ORCAMENTO_PEDIR_PEDIDO":
            # Check for Media (Photo or Document)
            if media_type in ["image", "document"]:
                session["status"] = "AGUARDANDO_HUMANO"
                # Save Order Info (mock)
                session["data"]["pedido_recebido"] = True
                reply_action = "ORDER_RECEIVED"
                reply_message = "Recebemos o seu pedido médico! 📸✅\nNossas atendentes irão verificar e calcular o orçamento para você. Por favor, aguarde um momento."
            
            # Check for Text Description
            elif len(message) > 5:
                 session["status"] = "AGUARDANDO_HUMANO"
                 session["data"]["pedido_descricao"] = message
                 reply_action = "ORDER_RECEIVED"
                 reply_message = "Certo, anotamos os exames: " + message + "\nNossas atendentes irão gerar o orçamento. Aguarde um momento. ⏳"
            
            else:
                 reply_message = "Por favor, envie a **foto do pedido** ou digite os nomes dos exames para prosseguirmos. 📸"

        elif current_status == "RESULTADO_PEDIR_COMPROVANTE":
             # 1. Accept valid Media
             if media_type in ["image", "document"]:
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "PROOF_RECEIVED"
                 reply_message = "Recebido! 📸\nVou verificar com a equipe se seu exame já está pronto e liberado. 📄✅\nAguarde um instante."
             
             # 2. Accept textual confirmation (Escape Valve)
             elif any(k in message.lower() for k in ["já enviei", "ja mandei", "enviei", "segue", "ta ai", "está aí", "anexo"]):
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "PROOF_RECEIVED"
                 reply_message = "Certo, entendi que você já enviou. 👍\nVou pedir para a equipe verificar. Aguarde um instante."

             # 3. Reject unrelated text/audio
             else:
                 reply_message = "Não consegui identificar o comprovante. 😕\nPor favor, envie a **FOTO** 📸 ou **PDF** do comprovante de pagamento/atendimento para liberarmos o resultado."

        elif current_status == "AGENDAMENTO_PEDIR_DADOS":
            session["data"]["address"] = message
            session["status"] = "AGUARDANDO_HUMANO"
            reply_action = "HANDOFF"
            reply_message = "Obrigado! Recebemos seus dados. Entraremos em contato para confirmar o horário da coleta. 🚐"

        elif current_status == "AGUARDANDO_HUMANO":
            # Silence mode: If human is talking, bot expects human to reply.
            # Only reset if explicit menu command
            if any(x in normalize_text_simple(message) for x in ["menu", "inicio", "comecar"]):
                 session["status"] = "MENU_PRINCIPAL"
                 reply_action = "SEND_MENU"
                 reply_message = "Voltando ao menu principal..."
            else:
                 # SILENCE
                 reply_message = None 

        session["last_updated"] = time.time()
        session["last_action"] = reply_action
        
        session["last_updated"] = time.time()
        session["last_action"] = reply_action
        
        # Persist to SQLite
        database.save_session(phone, session)
        
        return {
            "status": session["status"],
            "reply_message": reply_message,
            "action": reply_action
        }

def normalize_text_simple(text):
    import re
    from unidecode import unidecode
    if not text: return ""
    return unidecode(text).lower()
