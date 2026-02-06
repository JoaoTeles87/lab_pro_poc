import json
import os
import time
from datetime import datetime
from src.core import database

SESSION_FILE = os.path.join("data", "sessions.json")
MOCK_DB_FILE = os.path.join("data", "mock_db.json")
SESSION_TIMEOUT = 3600 # 1 hour

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

        # RE-ENGAGEMENT LOGIC
        # If the session was previously finalized (archived), receiving a new message
        # should wake it up as a fresh interaction.
        if current_status == "FINALIZADO":
            current_status = "MENU_PRINCIPAL"
            # Optional: Clear old data? Likely yes, to start fresh.
            saved_name = session["data"].get("name")
            session["data"] = {}
            if saved_name: session["data"]["name"] = saved_name
            # Don't reset history, let it append.
        
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
        
        # ADMIN COMMAND (Human Override)
        # Allows the human attendant to type "#bot" or "#reset" to return control to AI
        if message.strip().lower() in ["#bot", "#reset", "#voltar"]:
             current_status = "MENU_PRINCIPAL"
             reply_action = "SEND_MENU"
             name_display = session["data"].get("name", "Cliente")
             reply_message = (f"🤖 Controle retornado ao Robô.\nOlá novamente, *{name_display}*! 👋\n"
                              "1. Orçamentos 💰\n"
                              "2. Resultados 🧪\n"
                              "3. Agendamento 📆\n"
                              "4. Toxicológico")
             
             # Reset session data but keep name
             saved_name = session["data"].get("name")
             session["data"] = {}
             if saved_name: session["data"]["name"] = saved_name

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

        # 1. GLOBAL GRATITUDE HANDLER (Runs in ALL states)
        # If user says "obrigado", "valeu", etc., just reply politely and keep state.
        gratitude_words = ["obrigado", "obrigada", "obg", "valeu", "grato", "grata", "agradecido", "agradecida", "joia", "beleza", "tá bem", "ta bem", "certo", "ok", "brigado", "brigada"]
        if any(x in normalize_text_simple(message) for x in gratitude_words) and len(message) < 20: 
             reply_action = "ACK"
             reply_message = "Disponha! Se precisar de algo, é só chamar. 😉 É sempre um prazer lhe atender."
             # Return IMMEDIATELY to prevent state transition
             return {
                "status": current_status,
                "reply_message": reply_message,
                "action": reply_action
             }

        if current_status == "MENU_PRINCIPAL":
            # 0. Global Audio Handoff Rule
            # Audio messages in the main menu often contain complex requests.
            # We skip bot logic and send directly to human.
            if media_type == "audio":
                 session["status"] = "AGUARDANDO_HUMANO"
                 reply_action = "HANDOFF_AUDIO"
                 reply_message = "Recebi seu áudio! \nVou transferir para um de nossos atendentes dar prosseguimento. \nAguarde que logo retornamos. ⏳"
            
            # Explicit Greeting Re-handling (to avoid "Sorry i didn't understand" for "Oi")
            elif intent == "GREETING" or any(x in normalize_text_simple(message) for x in ["oi", "ola", "comecar", "inicio", "bom dia", "boa tarde", "boa noite", "tarde", "dia", "noite"]):
                 # CHECK NAME FIRST
                 current_name = session["data"].get("name")
                 if not current_name:
                      session["status"] = "CADASTRO_PEDIR_NOME"
                      reply_action = "ASK_NAME"
                      reply_message = "Olá! Tudo bem? Antes de prosseguir, qual é o seu nome?"
                 else:
                      reply_action = "SEND_MENU"
                      reply_message = (f"Olá novamente, *{current_name}*! 👋\n"
                                   "1. Solicitação de orçamentos 💰\n"
                                   "2. Solicitação de resultados 🧪\n"
                                   "3. Agendamento domiciliar 📆\n"
                                   "4. Toxicológico")
            
            # Smart Inference: If user mentions a Plan directly (e.g. "Bradesco"), assume ORCAMENTO
            elif entities.get("PLANO_SAUDE"):
                plan = entities["PLANO_SAUDE"]
                friendly_plan = PLAN_NAMES.get(plan, plan)
                session["data"]["plano"] = plan
                session["status"] = "ORCAMENTO_PEDIR_PEDIDO"
                reply_action = "ASK_ORDER"
                reply_message = f"Entendi, plano *{friendly_plan}*. 🏥\nPara orçamentos, por favor envie uma *foto do pedido médico* 📸 ou digite os exames."
            
            elif intent == "ORCAMENTO":
                session["status"] = "ORCAMENTO_PEDIR_PLANO"
                reply_action = "ASK_PLAN"
                reply_message = "Certo, Orçamentos. 💰\nVocê possui plano de saúde ou pagamento *à vista/sem plano*?\n(Ex: CASSI, BM, CLINMELO, Particular)"
            
            elif intent == "RESULTADO":
                session["status"] = "RESULTADO_PEDIR_COMPROVANTE"
                reply_action = "ASK_PROOF"
                reply_message = "Para verificar seus resultados 🧪, por favor envie a *foto do comprovante* de pagamento/atendimento. 📸"
            
            elif intent == "AGENDAMENTO":
                session["status"] = "AGENDAMENTO_PEDIR_PLANO"
                reply_action = "ASK_PLAN_SCHED"
                reply_message = "Agendamento Domiciliar 🏠.\nPara iniciar, qual seu *Plano de Saúde* ou seria *Particular*?\n(Aceitamos: CASSI, BM, CLINMELO ou Particular)"
                
            elif intent == "TOXICOLOGICO":
                reply_action = "INFO_TOXIC"
                reply_message = "O exame Toxicológico 🚦 é realizado por agendamento.\nAtendimento *somente Particular* (R$ 150,00) ou *Pagamento à vista*.\nNecessário CNH. \nDeseja realizar?"
                session["status"] = "TOXICOLOGICO_AGUARDANDO_RESPOSTA"
            
            # elif any(x in normalize_text_simple(message) for x in ["ok", "ta bem", "tá bem", "certo", "obrigado", "obg", "valeu", "entendi", "joia", "beleza"]):
            #    # Handle simple acknowledgments without sending the full menu
            #    reply_action = "ACK"
            #    reply_message = "Disponha! Se precisar de algo, é só chamar. 😉"
            #    # Keep in MENU_PRINCIPAL (passive)

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
                    reply_message = (f"Olá, *{name_display}*! Tudo bem? ✅\n\n"
                                        "Em que posso ajudar hoje? 😄\n\n"
                                        "1. Orçamentos 💰\n"
                                        "2. Resultados de exames 🧪\n"
                                        "3. Agendamento Domiciliar 📆\n"
                                        "4. Toxicológico (CNH)")

        elif current_status == "CADASTRO_PEDIR_NOME":
            # Capture Name
            clean_name = message.strip()
            
            # ESCAPE VALVE: If user ignores the question and sends a long sentence or question
            # We assume it's NOT a name, but a request.
            # Criteria: > 4 words OR > 25 chars OR contains "?"
            if len(clean_name.split()) > 4 or len(clean_name) > 25 or "?" in clean_name:
                 session["data"]["name"] = "Cliente" # Default
                 session["status"] = "MENU_PRINCIPAL" # Restore state
                 
                 # PROCESS THE MESSAGE AGAIN (Recursive call? Or simple fallthrough?)
                 # Simple Fallthrough is hard because we are in an elif block. 
                 # We will return a special "REPROCESS" action or just handle the reply manually.
                 
                 # Let's try to handle it by simulating the Menu Logic here for this turn.
                 # Actually, the best way is to set name and return "I didn't understand, here is the menu" 
                 # OR try to detect intent now.
                 
                 # Let's detect intent here:
                 if intent in ["ORCAMENTO", "RESULTADO", "AGENDAMENTO", "TOXICOLOGICO"]:
                      # If valid intent found, acknowledge and delegate in next turn? 
                      # No, let's reply with the menu to be safe, but acknowledged.
                      reply_action = "SEND_MENU"
                      reply_message = (f"Olá! Tudo bem? ✅\n"
                                         "Em que posso ajudar hoje? 😄\n\n"
                                         "1. Orçamentos 💰\n"
                                         "2. Resultados de exames 🧪\n"
                                         "3. Agendamento Domiciliar 📆\n"
                                         "4. Toxicológico (CNH)")
                 else:
                     # General Menu
                     reply_action = "SEND_MENU"
                     reply_message = (f"Olá! Tudo bem? ✅\n"
                                      "Em que posso ajudar hoje? 😄\n\n"
                                      "1. Orçamentos 💰\n"
                                      "2. Resultados de exames 🧪\n"
                                      "3. Agendamento Domiciliar 📆\n"
                                      "4. Toxicológico (CNH)")

            elif len(clean_name) > 2:
                session["data"]["name"] = clean_name.title()
                session["status"] = "MENU_PRINCIPAL"
                reply_action = "WELCOME"
                reply_message = (f"Obrigado, *{clean_name.title()}*! Prazer em te conhecer. ✨\n\n"
                                 "Como posso te ajudar?\n\n"
                                     "1. Orçamentos 💰\n"
                                     "2. Resultados de exames 🧪\n"
                                     "3. Agendamento Domiciliar 📆\n"
                                     "4. Toxicológico")
            else:
                reply_message = "Nome muito curto. Por favor, digite seu nome completo."

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
                 reply_message = "Anotei aqui: " + message + "\nVou calcular o orçamento. Aguarde um pouquinho. ⏳"
            
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
                PLAN_NAMES = { "CASSI": "CASSI", "BM": "BM", "CLINMELO": "Clinmelo", "PARTICULAR": "Particular" }
                friendly_plan = PLAN_NAMES.get(chosen_plan, chosen_plan)

                session["data"]["plano"] = chosen_plan
                session["status"] = "AGENDAMENTO_PEDIR_DADOS"
                reply_action = "ASK_ADDR"
                reply_message = f"Certo, plano *{friendly_plan}*. Agora, qual o seu *Endereço* para a gente ver a rota? 🚐"
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
    text = unidecode(text).lower()
    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    return text
