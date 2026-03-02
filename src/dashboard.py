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
def load_data(client_id=None):
    return database.get_all_sessions(client_id)

def clear_data(client_id):
    database.clear_all_sessions(client_id)
    st.toast(f"Histórico da clínica {client_id} limpo! 🧹", icon="✅")
    time.sleep(1)
    st.rerun()

# --- SIDEBAR: CLIENT SELECTION ---
with st.sidebar:
    st.title("🏥 Unidades")
    # Get all sessions to find unique clientIds
    all_raw = database.get_all_sessions()
    # Note: our get_all_sessions returns dict {phone: data}, and data now has client_id
    # Wait, in database.py get_all_sessions returns all. 
    # Let's adjust logic to find distinct client_ids.
    
    # We'll just list some common ones for now or extract from data
    available_clients = sorted(list(set(s.get("client_id", "desconhecido") for s in all_raw.values())))
    if not available_clients:
        available_clients = ["clinica_teste"]
        
    selected_client = st.selectbox("Selecione a Clínica", available_clients)
    st.info(f"Visualizando: **{selected_client}**")
    
    if st.button("🗑️ Limpar Clínica Atual"):
        clear_data(selected_client)

st.title("📊 Painel Multiclínicas - Lab Pró-Análise")
st.markdown(f"Monitoramento em tempo real para: **{selected_client}**")
st.caption("✅ Conexão Segura | 🔒 Autenticado")

# Header Actions
col_kpi, col_actions = st.columns([3, 1])

with col_actions:
    if st.button("🔄 Atualizar"):
        st.rerun()

# Load specific client data
sessions = load_data(selected_client)

with placeholder.container():
    # KPI Row
    total = len(sessions)
    waiting = sum(1 for s in sessions.values() if s.get("status") == "AGUARDANDO_HUMANO")
    in_progress = sum(1 for s in sessions.values() if s.get("status") not in ["AGUARDANDO_HUMANO", "FINALIZADO"])
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sessões", total)
    c2.metric("Em Atendimento (Robô)", in_progress)
    c3.metric("Aguardando Humano", waiting)
    
    st.markdown("---")
    
    # Columns for Kanban
    col_robot, col_human, col_done = st.columns(3)
    
    with col_robot:
        st.subheader("🤖 Em Atendimento")
        robot_sessions = [s for s in sessions.values() if s.get("status") not in ["AGUARDANDO_HUMANO", "FINALIZADO"]]
        if not robot_sessions:
            st.info("Nenhuma sessão ativa.")
        
        for data in robot_sessions:
            phone = data.get("phone")
            status = data.get("status")
            with st.container(border=True):
                patient_name = data.get("data", {}).get("name")
                if patient_name:
                        st.markdown(f"**👤 {patient_name}**")
                        st.caption(f"📞 {phone}")
                else:
                        st.markdown(f"**📞 {phone}**")
                st.caption(f"Status: `{status}`")
                st.caption(f"Interações: {data.get('interaction_count', 1)}")
                
                last_history_item = data.get('history', [])[-1] if data.get('history') else {}
                st.write(f"**Intenção:** {last_history_item.get('intent', 'N/A')}")
                st.text(f"Msg: {last_history_item.get('message', '')[:50]}...")

    with col_human:
        st.subheader("👨‍⚕️ Aguardando Humano")
        human_sessions = [s for s in sessions.values() if s.get("status") == "AGUARDANDO_HUMANO"]
        if not human_sessions:
            st.info("Fila vazia. 🙌")
        
        for data in human_sessions:
            phone = data.get("phone")
            created_at = data.get("created_at", time.time())
            elapsed_min = (time.time() - created_at) / 60
            
            with st.container(border=True):
                patient_name = data.get("data", {}).get("name")
                if patient_name:
                        st.markdown(f"## 👤 {patient_name}")
                        st.caption(f"📞 {phone}")
                else:
                        st.markdown(f"**📞 {phone}**")
                if elapsed_min > 10:
                    st.warning(f"⚠️ SLA Estourado (+{int(elapsed_min)} min)")
                else:
                    st.info("Dentro do prazo")
                
                if st.button("✅ Finalizar", key=f"btn_finalize_{selected_client}_{phone}"):
                    data["status"] = "FINALIZADO"
                    database.save_session(selected_client, phone, data)
                    st.toast(f"Sessão {phone} finalizada!")
                    time.sleep(1)
                    st.rerun()

    with col_done:
        st.subheader("✅ Finalizados")
        finalized_count = sum(1 for s in sessions.values() if s.get("status") == "FINALIZADO")
        if finalized_count > 0:
            st.metric("Atendimentos Concluídos", finalized_count)
        else:
            st.info("Nenhum atendimento finalizado.")

time.sleep(REFRESH_RATE)
st.rerun()

time.sleep(REFRESH_RATE)
st.rerun()
