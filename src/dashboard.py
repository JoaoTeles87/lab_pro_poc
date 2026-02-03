import streamlit as st
import json
import os
import time
from datetime import datetime
from src.core import database

# Page Setup
st.set_page_config(page_title="Painel de Controle - Lab Pró-Análise", layout="wide", page_icon="🧪")

# --- AUTHENTICATION ---
# Simple password check using environment variable or default
ADMIN_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "lab123")

if "auth" not in st.session_state:
    st.session_state.auth = False

def check_password():
    if st.session_state.password_input == ADMIN_PASSWORD:
        st.session_state.auth = True
    else:
        st.error("Senha incorreta!")

if not st.session_state.auth:
    st.title("🔒 Acesso Restrito")
    st.text_input("Senha de Acesso", type="password", key="password_input", on_change=check_password)
    st.stop() # Stop execution if not authenticated

# --- CONFIG ---
REFRESH_RATE = 10 # seconds (Updated to prevent flickering)

# --- DATA LOADER ---
def load_data():
    return database.get_all_sessions()

def clear_data():
    database.clear_all_sessions()
    st.toast("Histórico limpo! 🧹", icon="✅")
    time.sleep(1)
    st.rerun()

st.title("📊 Painel de Controle - Lab Pró-Análise")
st.markdown("Monitoramento em tempo real (SQLite).")
st.caption("✅ Conexão Segura | 🔒 Autenticado")

# Header Actions
col_kpi, col_actions = st.columns([3, 1])

with col_actions:
    if st.button("🔄 Atualizar"):
        st.rerun()
    
    if st.button("🗑️ Limpar Histórico"):
        clear_data()

# Auto-refresh using empty container hack
placeholder = st.empty()

sessions = load_data()

with placeholder.container():
    # KPI Row
    total = len(sessions)
    waiting = sum(1 for s in sessions.values() if s.get("status") == "AGUARDANDO_HUMANO")
    in_progress = sum(1 for s in sessions.values() if s.get("status") != "AGUARDANDO_HUMANO" and s.get("status") != "FINALIZADO")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sessões", total)
    c2.metric("Em Atendimento (Robô)", in_progress)
    c3.metric("Aguardando Humano", waiting)
    
    st.markdown("---")
    
    # Columns for Kanban
    col_robot, col_human, col_done = st.columns(3)
    
    with col_robot:
        st.subheader("🤖 Em Atendimento")
        # Check if empty
        robot_sessions = [s for s in sessions.values() if s.get("status") and s.get("status") != "AGUARDANDO_HUMANO" and s.get("status") != "FINALIZADO"]
        if not robot_sessions:
            st.info("Nenhuma sessão ativa.")
        
        for data in robot_sessions:
            phone = data.get("phone") # Ensure we get phone from data if iterating values
            if not phone: continue # Should not happen
            
            status = data.get("status")
            with st.container(border=True):
                # Name Resolution
                patient_name = data.get("data", {}).get("name")
                if patient_name:
                        st.markdown(f"**👤 {patient_name}**")
                        st.caption(f"📞 {phone}")
                else:
                        st.markdown(f"**📞 {phone}**")
                
                st.caption(f"Status: `{status}`")
                
                count = data.get("interaction_count", 1)
                st.caption(f"Interações: {count}")

                last_history_item = data.get('history', [])[-1] if data.get('history') else {}
                last_intent = last_history_item.get('intent', 'N/A')
                st.write(f"**Intenção:** {last_intent}")
                
                last_msg = last_history_item.get('message', '')
                st.text(f"Msg: {last_msg[:50]}...")

    with col_human:
        st.subheader("👨‍⚕️ Aguardando Humano")
        human_sessions = [s for s in sessions.values() if s.get("status") == "AGUARDANDO_HUMANO"]
        
        if not human_sessions:
            st.info("Fila vazia. 🙌")
        
        for data in human_sessions:
            phone = data.get("phone")
            
            # SLA Check
            created_at = data.get("created_at", time.time())
            elapsed_min = (time.time() - created_at) / 60
            is_late = elapsed_min > 10
            
            with st.container(border=True):
                    # Name Resolution for Human Queue
                patient_name = data.get("data", {}).get("name")
                if patient_name:
                        st.markdown(f"## 👤 {patient_name}")
                        st.caption(f"📞 {phone}")
                else:
                        st.markdown(f"**📞 {phone}**")

                if is_late:
                    st.warning(f"⚠️ SLA Estourado (+{int(elapsed_min)} min)")
                else:
                    st.info("Dentro do prazo")
                
                # Use a specific prefix for the key to ensure uniqueness relative to other potential buttons
                if st.button("✅ Finalizar", key=f"btn_finalize_{phone}"):
                    # Move to 'Done' column instead of deleting
                    data["status"] = "FINALIZADO"
                    database.save_session(phone, data)
                    st.toast(f"Sessão {phone} finalizada!")
                    time.sleep(1)
                    st.rerun()

    with col_done:
        st.subheader("✅ Finalizados")
        finalized_count = sum(1 for s in sessions.values() if s.get("status") == "FINALIZADO")
        
        if finalized_count > 0:
            st.metric("Atendimentos Concluídos", finalized_count)
            st.caption("Pacientes que já tiveram atendimento encerrado.")
        else:
            st.info("Nenhum atendimento finalizado.")

time.sleep(REFRESH_RATE)
st.rerun()
