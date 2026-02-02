#!/bin/bash

# Lab Pró-Análise - Bare Metal Installer for Ubuntu/Debian
# Usage: chmod +x install.sh && ./install.sh

echo "🚀 Iniciando instalação Bare Metal..."

# 1. Update System
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3 & Node.js
echo "📦 Instalando dependências (Python, Node, FFmpeg)..."
sudo apt install -y python3-pip python3-venv ffmpeg nodejs npm

# 3. Install PM2 (Process Manager)
echo "⚙️ Instalando PM2..."
sudo npm install -g pm2

# 4. Setup Python Backend
echo "🐍 Configurando Backend Python..."
python3 -m venv .venv
source .venv/bin/activate
pip install uv
uv sync # Or pip install -r requirements.txt if using standard pip
# Install actual deps
pip install fastapi uvicorn requests unidecode python-dotenv openai-whisper

# 5. Setup Node Gateway
echo "🌐 Configurando Gateway..."
cd whatsapp-gateway
npm install
cd ..

# 6. Start Everything
echo "🔥 Iniciando serviços com PM2..."
# We use the venv python for the backend
pm2 start ecosystem.config.js --interpreter ./.venv/bin/python3

# 7. Save startup list
pm2 save
pm2 startup

echo "✅ Instalação concluída!"
echo "📡 Backend rodando em: http://127.0.0.1:8000"
echo "📡 Gateway rodando em: http://127.0.0.1:3000"
echo "📋 Use 'pm2 status' para ver os serviços."
