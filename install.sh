#!/bin/bash

# Lab Pró-Análise - Bare Metal Installer for Ubuntu/Debian
# Usage: chmod +x install.sh && ./install.sh

echo "🚀 Iniciando instalação Bare Metal..."

# 1. Update System
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3 & Node.js
echo "📦 Instalando dependências (Python, Node, FFmpeg)..."
# Ubuntu/Debian often separate venv module. Installing it explicitly prevents ensurepip package errors.
# 'npm' is usually bundled with 'nodejs' from NodeSource, so we don't install it separately to avoid conflicts.
sudo apt install -y python3-pip python3-venv ffmpeg nodejs

# 3. Install PM2 (Process Manager)
echo "⚙️ Instalando PM2..."
sudo npm install -g pm2

# 4. Setup Python Backend
echo "🐍 Configurando Backend Python..."
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies inside venv
pip install uv
uv sync 2>/dev/null || pip install -r requirements.txt
pip install fastapi uvicorn requests unidecode python-dotenv

# 5. Setup Node Gateway
echo "🌐 Configurando Gateway..."
cd whatsapp-gateway
npm install
cd ..

# 6. Start Everything
echo "🔥 Iniciando serviços com PM2..."
# Delete old processes if they exist
pm2 delete lab-backend 2>/dev/null
pm2 delete lab-gateway 2>/dev/null

# Start using ecosystem
pm2 start ecosystem.config.js

# 7. Save startup list
pm2 save
pm2 startup

echo "✅ Instalação concluída!"
echo "📡 Backend rodando em: http://127.0.0.1:8000"
echo "📡 Gateway rodando em: http://127.0.0.1:3000"
echo "📋 Use 'pm2 status' para ver os serviços."
