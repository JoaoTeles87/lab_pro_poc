import json
import os
import time
from datetime import datetime
from src.core import database
from src.config import IGNORED_NUMBERS, TEST_PREFIX

SESSION_FILE = os.path.join("data", "sessions.json")
MOCK_DB_FILE = os.path.join("data", "mock_db.json")
SESSION_TIMEOUT = 900 # 15 minutes for automated flows
HUMAN_SESSION_TIMEOUT = 7200 # 2 hours for human mode (7200s)

PLAN_NAMES = {
    "CASSI": "CASSI",
    "BM": "PMPB / AFRAFEP / GEAP",
    "CLINMELO": "Clinmelo",
    "PARTICULAR": "Particular / Cartão / Pix"
}

class SessionManager:
    def __init__(self):
        # Initialize DB on startup
        database.init_db()
        # Auto-maintenance: Prune old sesions (>120 days / 4 months)
        database.prune_old_sessions(120)
        
        # Mock DB for results lookup (read-only json)
        self.mock_db_path = MOCK_DB_FILE
        self._load_mock_db()

    def get_session(self, client_id: str, phone: str) -> dict:
        """Loads session from DB or creates new."""
        session = database.get_session(client_id, phone)
        if not session:
             session = {
                "client_id": client_id,
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

    def check_results(self, client_id: str, protocol_or_cpf: str):
        # Implement Logic to check Mock DB within client scope
        clinica_data = self.mock_db.get(client_id, {})
        patients = clinica_data.get("patients", {})
        
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

    def update_session(self, client_id: str, phone: str, message: str, intent: str, entities: dict, contact_name: str = None, media_type: str = "text", from_me: bool = False):
        # --- IGNORED NUMBERS / TEST MODE ---
        is_ignored = phone in IGNORED_NUMBERS
        is_test_mode = message.startswith(TEST_PREFIX)

        if is_ignored:
            if is_test_mode:
                # Strip prefix and proceed
                message = message[len(TEST_PREFIX):].strip()
                if not message:
                    message = "oi" # Default to greeting
                print(f"   [SESSION] Ignored number {phone} in TEST MODE. Proceeding with message: {message}")
            else:
                print(f"   [SESSION] Ignoring message from ignored number: {phone}")
                return None

        session = self.get_session(client_id, phone)
        
        # --- HUMAN HANDOFF (fromMe) ---
        # If message is from the attendant, mark as AGUARDANDO_HUMANO and renew timeout
        if from_me:
            print(f"   [SESSION] Detected message from attendant for {phone}. Setting AGUARDANDO_HUMANO.")
            session["status"] = "AGUARDANDO_HUMANO"
            session["last_updated"] = time.time()
            database.save_session(client_id, phone, session)
            # No reply needed as this was the reply
            return None
        
        # Increment Interaction Count (new conversations)
        if intent == "GREETING" or session["interaction_count"] == 0:
            session["interaction_count"] += 1

        # --- NAME REGISTRATION Logic (REMOVED AGGRESSIVE INTERRUPT) ---
        # We now only ask for name if the user GREETS us or explicitly enters the flow.
        # Logic moved to MENU_PRINCIPAL block.
        
        # --- FILTER INVALID MESSAGES ---
        # 0. STRICT FILTER: Ignore empty/whitespace messages or emoji-only/symbol-only if no intent
        if not intent and media_type == "text":
             # Normalize heavily to see if there are actual letters/numbers
             clean_text = normalize_text_simple(message)
             clean_text = ''.join(c for c in clean_text if c.isalnum()) # Keep only alnum
             
             if len(clean_text) < 2:
                 # Check if it was a critical digit like '1', '2' (Intents would usually catch this, but just in case)
                 if message.strip() in ["1", "2", "3", "4"]:
                     pass # Allow
                 else:
                     print(f"   [SESSION] Ignoring invalid/empty message: {message}")
                     return None


        # --- TIMEOUT CHECK ---
        # Current State
        current_status = session.get("status", "MENU_PRINCIPAL")

        now = time.time()
        last_ts = session.get("last_updated", 0)
        
        # 24 hours for human mode, 15 minutes for automated flows
        timeout_limit = HUMAN_SESSION_TIMEOUT if current_status == "AGUARDANDO_HUMANO" else SESSION_TIMEOUT
        
        if last_ts > 0 and (now - last_ts) > timeout_limit:
             if current_status == "AGUARDANDO_HUMANO":
                 print(f"[SESSION] 2h Timeout detected for {phone}. Resetting to MENU.")
                 session["status"] = "MENU_PRINCIPAL"
                 current_status = "MENU_PRINCIPAL"
                 # Flag that we came from a stale human session to allow silent reset
                 session["data"]["was_stale_human"] = True
             else:
                 print(f"[SESSION] Inactivity > 15m detected for {phone}. Yielding to HUMAN.")
                 session["status"] = "AGUARDANDO_HUMANO"
                 current_status = "AGUARDANDO_HUMANO"
                 
             session["data"].pop("interaction_count", None) # Optional: don't clear all data if needed?
             # But usually we clear flow data for fresh start
             session["data"] = {k: v for k, v in session["data"].items() if k == "was_stale_human"} 
             session["interaction_count"] += 1 # New interaction flow

        # Update last_updated for the current interaction
        session["last_updated"] = now


        session["history"].append({
            "timestamp": now,
            "role": "user",
            "message": message,
            "intent": intent
        })

        # --- STATE MACHINE ---
        
        reply_action = None
        reply_message = None

        # RE-ENGAGEMENT LOGIC
        # If the session was previously finalized (archived), receiving a new message
        # should wake it up as a fresh interaction.
        if current_status == "FINALIZADO":
            current_status = "MENU_PRINCIPAL"
            # Optional: Clear old data? Likely yes, to start fresh.
            session["data"] = {}
            # Don't reset history, let it append.
        
        # RESET logic (if user says "oi", "ola", "menu" intentionally)
        # Note: if users says "oi" inside a flow, we might want to reset or ignore.
        # For this POC, strong reset on specific keywords helps navigation.
        # RESET logic (if user says "oi", "ola", "menu" intentionally)
        # Note: We now allow reset even in 'AGUARDANDO_HUMANO' if the input is an explicit command (1-5) or greeting.
        is_reset_input = (intent == "GREETING" or 
                          any(x in normalize_text_simple(message) for x in ["oi", "ola", "comecar", "menu", "inicio", "bom dia", "boa tarde", "boa noite"]) or 
                          message.strip() in ["1", "2", "3", "4", "5"])
        
        if is_reset_input:
             current_status = "MENU_PRINCIPAL"
             # Clear the stale flag if user interacted
             session["data"].pop("was_stale_human", None)
             # Clear data
             session["data"] = {}
        
        # ADMIN COMMAND (Human Override)
        # Allows the human attendant to type "#bot" or "#reset" to return control to AI
        if message.strip().lower() in ["#bot", "#reset", "#voltar"]:
             current_status = "MENU_PRINCIPAL"
             reply_action = "SEND_MENU"
             reply_message = ("🤖 Controle retornado ao Robô.\nOlá novamente! 👋\n"
                              "1. Orçamentos 💰\n"
                              "2. Resultados 🧪\n"
                              "3. Agendamento 📆\n"
                              "4. Toxicológico(CNH)\n"
                              "5. Outras dúvidas\n"
                              "• Pedimos que siga as instruções e aguarde nosso atendimento")
             
             # Reset session data
             session["data"] = {}

        # Helper for Friendly Plan Names
        PLAN_NAMES = {
            "CASSI": "CASSI",
            "BM": "BM",
            "CLINMELO": "Clinmelo",
            "PARTICULAR": "Private", # Internal, mapped below
            "ID_CASSI": "CASSI",
            "ID_BM": "BM",
            "ID_CLINMELO": "Clinmelo",
            "ID_PARTICULAR": "Particular"
        }
        
        
        # LOGIC
 
        # LOGIC
        # 0. STRICT FILTER: Ignore empty/whitespace messages (Double check)
        if not message or not message.strip():
            return None # Do nothing

        # 1. INTELLIGENT SILENT RESET (Priority 1)
        # If we just came from a timeout in AGUARDANDO_HUMANO, we stay silent UNLESS
        # the user sends a greeting, a clear intent, or an explicit menu option.
        is_greeting = (intent == "GREETING" or any(x in normalize_text_simple(message) for x in ["oi", "ola", "comecar", "inicio", "bom dia", "boa tarde", "boa noite", "menu"]))
        is_menu_opt = message.strip() in ["1", "2", "3", "4", "5"]
        
        if session["data"].get("was_stale_human"):
            # If it's NOT a greeting, NOT a menu option, and NO clear intent found
            if not is_greeting and not is_menu_opt and not intent:
                session["data"].pop("was_stale_human", None)
                print(f"   [SESSION] Intelligent Silent Reset for {phone}")
                database.save_session(client_id, phone, session)
                return None
            else:
                # User interacted with something valid, clear the flag and proceed
                session["data"].pop("was_stale_human", None)

        # 2. GLOBAL GRATITUDE HANDLER (Runs in ALL states, except AGUARDANDO_HUMANO)
        # If user says "obrigado", "valeu", etc., just reply politely and keep state.
        gratitude_words = ["obrigado", "obrigada", "obg", "valeu", "grato", "grata", "agradecido", "agradecida", "joia", "beleza", "tá bem", "ta bem", "certo", "ok", "brigado", "brigada"]
        if current_status != "AGUARDANDO_HUMANO" and any(x in normalize_text_simple(message) for x in gratitude_words) and len(message) < 20: 
             reply_action = "ACK"
             reply_message = "Disponha! Se precisar de algo, é só chamar. 😉 É sempre um prazer lhe atender."
             return {
                "status": current_status,
                "reply_message": reply_message,
                "action": reply_action
             }

        if current_status == "MENU_PRINCIPAL":
            # 0. Global Audio Handoff Rule
            if media_type == "audio":
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "HANDOFF_AUDIO"
                 reply_message = "Recebi seu áudio! \nVou transferir para um de nossos atendentes dar prosseguimento. \nAguarde que logo retornamos. ⏳"
            
            # 1. Greetings / Reset Explicitly
            elif intent == "GREETING" or any(x in normalize_text_simple(message) for x in ["oi", "ola", "comecar", "inicio", "bom dia", "boa tarde", "boa noite", "menu"]):
                  reply_action = "SEND_MENU"
                  reply_message = ("Olá! Tudo bem? ✅\n\n"
                               "1. Solicitação de orçamentos 💰\n"
                               "2. Solicitação de resultados 🧪\n"
                               "3. Agendamento domiciliar 📆\n"
                               "4. Toxicológico (CNH)\n"
                               "5. Outras dúvidas\n"
                               "• Pedimos que siga as instruções e aguarde nosso atendimento")
            
            # 2. Results Intent
            elif intent == "RESULTADO":
                session["status"] = "RESULTADO_PEDIR_COMPROVANTE"
                reply_action = "ASK_PROOF"
                reply_message = "Para verificar seus resultados 🧪, por favor envie a *foto do comprovante* de pagamento/atendimento. 📸"
            
            # 3. Budget Intent
            elif intent == "ORCAMENTO" or entities.get("PLANO_SAUDE"):
                # If they already mentioned a plan, skip the first question
                if entities.get("PLANO_SAUDE"):
                    plan = entities["PLANO_SAUDE"]
                    session["data"]["plano"] = plan
                    session["status"] = "ORCAMENTO_PEDIR_PEDIDO"
                    reply_action = "ASK_ORDER"
                    friendly_plan = PLAN_NAMES.get(plan, plan)
                    reply_message = f"Entendi, plano *{friendly_plan}*. 🏥\nPara orçamentos, por favor envie uma *foto do pedido médico* 📸 ou digite os exames."
                else:
                    session["status"] = "ORCAMENTO_PEDIR_PLANO"
                    reply_action = "ASK_PLAN"
                    reply_message = "Certo, Orçamentos. 💰\nVocê possui plano de saúde ou pagamento *à vista/sem plano*?\n(Ex: CASSI, BM, CLINMELO, Particular)"

            # 4. Schedule Intent
            elif intent == "AGENDAMENTO":
                session["status"] = "AGENDAMENTO_PEDIR_PLANO"
                reply_action = "ASK_PLAN_SCHED"
                reply_message = "Agendamento Domiciliar 🏠.\nPara iniciar, qual seu *Plano de Saúde* ou seria *Particular*?\n(Aceitamos: CASSI, BM, CLINMELO ou Particular)"
                
            # 5. Toxic Intent
            elif intent == "TOXICOLOGICO":
                reply_action = "INFO_TOXIC"
                reply_message = "O exame Toxicológico 🚦 é realizado por agendamento.\nAtendimento *somente Particular* (R$ 150,00) ou *Pagamento à vista*.\nNecessário CNH. \nDeseja realizar?"
                session["status"] = "TOXICOLOGICO_AGUARDANDO_RESPOSTA"

            # 6. Option 5 - Explicit Handoff
            elif message.strip() == "5" or "outras duvidas" in normalize_text_simple(message):
                session["status"] = "AGUARDANDO_HUMANO"
                reply_action = "HANDOFF_DUVIDAS"
                reply_message = "Entendido! Você será transferido para um de nossos atendentes. Aguarde um momento. ⏳"

            # 7. Fallback (Normal MENU loop or handoff)
            else:
                # Long Message / Complexity Handoff
                if len(message) > 60:
                        session["status"] = "AGUARDANDO_HUMANO"
                        reply_action = "HANDOFF_COMPLEX"
                        reply_message = "Estou transferindo para um de nossos atendentes analisarem sua mensagem. Aguarde um momento. ⏳"
                else:
                    last_act = session.get("last_action")
                    if last_act in ["SEND_MENU", "WELCOME", "SENT_SHORT_MENU"]:
                        reply_action = "SENT_SHORT_MENU"
                        reply_message = ("Desculpe, não entendi. 😕\nPoderia repetir ou digitar o número?\n\n"
                                        "1. Orçamentos 💰\n"
                                        "2. Resultados 🧪\n"
                                        "3. Agendamento 📆\n"
                                        "4. Toxicológico (CNH)\n"
                                        "5. Outras dúvidas\n"
                                        "• Pedimos que siga as instruções ou aguarde um atendente.")
                    else:
                        reply_action = "SEND_MENU"
                        reply_message = ("Olá! 👋 Em que posso ajudar hoje? ✅\n\n"
                                        "1. Orçamentos 💰\n"
                                        "2. Resultados 🧪\n"
                                        "3. Agendamento 📆\n"
                                        "4. Toxicológico (CNH)\n"
                                        "5. Outras dúvidas\n"
                                        "• Pedimos que siga as instruções ou aguarde um atendente.")


        elif current_status == "ORCAMENTO_PEDIR_PLANO":
            # Capture Plan (Regex/Keyword Logic)
            msg_lower = message.lower()
            chosen_plan = None
            
            # 1. Try Entity Extraction first
            if entities.get("PLANO_SAUDE"):
                chosen_plan = entities.get("PLANO_SAUDE")
            
            # 2. Fallback to simple keyword match if entity failed
            elif any(x in msg_lower for x in ["particular", "dinheiro", "pix", "vista", "sem plano"]):
                chosen_plan = "PARTICULAR"
            elif "cassi" in msg_lower:
                chosen_plan = "CASSI"
            elif any(x in msg_lower for x in ["bm", "b m", "militar"]):
                chosen_plan = "BM"
            elif "clinmelo" in msg_lower:
                chosen_plan = "CLINMELO"

            if chosen_plan:
                # Map Internal ID to Friendly Name
                friendly_plan = PLAN_NAMES.get(chosen_plan, chosen_plan)
                if chosen_plan == "PARTICULAR": friendly_plan = "Particular" # Override internal ID if needed

                session["data"]["plano"] = chosen_plan
                session["status"] = "ORCAMENTO_PEDIR_PEDIDO"
                reply_action = "ASK_ORDER"
                reply_message = f"Certo, plano *{friendly_plan}*. Agora, tire uma *foto do pedido médico* 📸 ou digite os exames e mande aqui."
            else:
                reply_message = "Aceitamos somente CASSI, BM, Clinmelo ou Particular (à vista)."

        elif current_status == "ORCAMENTO_PEDIR_PEDIDO":
            # Check for Media (Photo or Document)
            if media_type in ["image", "document"]:
                session["status"] = "AGUARDANDO_HUMANO"
                # Save Order Info (mock)
                session["data"]["pedido_recebido"] = True
                reply_action = "ORDER_RECEIVED"
                reply_message = "Recebi o pedido! 📸✅\nVou ver o preço para você. Só um momento."
            
            # Check for Text Description
            elif len(message) > 5:
                 session["status"] = "AGUARDANDO_HUMANO"
                 session["data"]["pedido_descricao"] = message
                 reply_action = "ORDER_RECEIVED"
                 reply_message = "Anotei aqui: " + message + "\nVou calcular o orçamento. Aguarde que logo entraremos em contato. ⏳"
            
            else:
                 reply_message = "Mande a *foto do pedido* ou escreva os exames, por favor. 📸"



        elif current_status == "AGENDAMENTO_PEDIR_PLANO":
            # Reuse logic or simplify
            msg_lower = message.lower()
            valid_plan = False
            chosen_plan = "PARTICULAR"

            if any(x in msg_lower for x in ["particular", "dinheiro", "pix", "vista"]):
                chosen_plan = "PARTICULAR"
                valid_plan = True
            elif "cassi" in msg_lower:
                chosen_plan = "CASSI"
                valid_plan = True
            elif any(x in msg_lower for x in ["bm", "b m", "militar"]):
                chosen_plan = "BM"
                valid_plan = True
            elif "clinmelo" in msg_lower or "clin melo" in msg_lower:
                chosen_plan = "CLINMELO"
                valid_plan = True
            
            # Check Entity
            plan_ent = entities.get("PLANO_SAUDE")
            if plan_ent:
                chosen_plan = plan_ent
                valid_plan = True
            
            if valid_plan:
                friendly_plan = PLAN_NAMES.get(chosen_plan, chosen_plan)

                session["data"]["plano"] = chosen_plan
                session["status"] = "AGENDAMENTO_PEDIR_DADOS"
                reply_action = "ASK_ADDR"
                reply_message = f"Certo, plano *{friendly_plan}*. Agora, qual o seu *Endereço* para a gente ver a rota e agendar o melhor dia para irmos até a residência. 🚐 \nLogo retornaremos!"
            else:
                 reply_message = "Não entendi qual é o plano. Aceitamos somente: CASSI, BM, Clinmelo ou Particular."

        elif current_status == "RESULTADO_PEDIR_COMPROVANTE":
             # 1. Accept valid Media
             if media_type in ["image", "document"]:
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "PROOF_RECEIVED"
                 reply_message = "Recebido! 📸\nVou verificar se já ficou pronto. Um momento. 📄✅"
             
             # 2. Accept textual confirmation (Escape Valve)
             elif any(k in message.lower() for k in ["já enviei", "ja mandei", "enviei", "segue", "ta ai", "está aí", "anexo"]):
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "PROOF_RECEIVED"
                 reply_message = "Ah, tudo bem. Vou pedir para as meninas verificarem. Só um instante."

             # 3. Reject unrelated text/audio
             else:
                 reply_message = "Preciso que você mande a *foto do comprovante* 📸 para eu achar o exame."

        elif current_status == "AGENDAMENTO_PEDIR_DADOS":
            session["data"]["address"] = message
            session["status"] = "AGUARDANDO_HUMANO"
            reply_action = "HANDOFF"
            reply_message = "Obrigado! Recebi o endereço.\nVamos entrar em contato para confirmar o horário. 🚐"

        elif current_status == "TOXICOLOGICO_AGUARDANDO_RESPOSTA":
            msg_lower = normalize_text_simple(message)
            # 1. Positive
            if any(x in msg_lower for x in ["sim", "quero", "pode ser", "s", "ok", "agendar", "fazer"]):
                 session["status"] = "TOXICOLOGICO_PEDIR_CNH"
                 reply_action = "ASK_CNH"
                 reply_message = "Perfeito. Para agendar, preciso da *foto da sua CNH* (Carteira de Motorista) ou dos dados da sua CNH. 📸"
            
            # 2. Negative / Gratitude
            elif any(x in msg_lower for x in ["nao", "não", "obrigado", "obg", "valeu", "deixa", "cancelar"]):
                 session["status"] = "MENU_PRINCIPAL"
                 reply_action = "ACK_CANCEL"
                 reply_message = "Sem problemas! Se mudar de ideia, é só chamar. 😉"
            
            else:
                 reply_message = "Desculpe, não entendi. Deseja realizar o exame Toxicológico? (Responda Sim ou Não)"

        elif current_status == "TOXICOLOGICO_PEDIR_CNH":
             if media_type in ["image", "document"]:
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "CNH_RECEIVED"
                 reply_message = "Recebi sua CNH! 📸✅\nVamos verificar a disponibilidade e entrar em contato. Aguarde. ⏳"
             else:
                  reply_message = "Por favor, envie a *foto da CNH* para prosseguirmos. 📸"

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

        # Persist to SQLite
        database.save_session(client_id, phone, session)
        
        return {
            "status": session["status"],
            "reply_message": reply_message,
            "action": reply_action
        }

def normalize_text_simple(text):
    import re
    from unidecode import unidecode
    if not text: return ""
    text = unidecode(text).lower()
    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    return text
