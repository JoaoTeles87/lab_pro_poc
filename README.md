# Lab Pró-Análise - WhatsApp SaaS Gateway (Multitenant)

Este repositório contém o MVP do sistema de automação para clínicas, refatorado para suporte multitenancy e otimização de recursos para VPS Oracle (1GB RAM).

## Arquitetura
- **Gateway (Node.js)**: Baseado em @whiskeysockets/baileys. Gerencia sessões WhatsApp com armazenamento em SQLite e "Idle Disconnect" para economia de memória.
- **Backend (Python/FastAPI)**: Gerencia a lógica do bot, triagem, e banco de dados de sessões e histórico.
- **Dashboard (Streamlit)**: Monitoramento em tempo real de todas as unidades clínicas.

## Como Rodar Localmente

### 1. Requisitos
- Node.js (v18+)
- Python (v3.10+)
- FFmpeg (Configurado no PATH)

### 2. Configuração do Backend (Python)
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute a migração do banco de dados (se houver dados antigos):
   ```bash
   python src/scripts/migration_v2.py
   ```
3. Inicie o servidor:
   ```bash
   python -m src.main
   ```

### 3. Configuração do Gateway (Node.js)
1. Entre na pasta:
   ```bash
   cd whatsapp-gateway
   ```
2. Instale as dependências:
   ```bash
   npm install
   ```
3. Inicie o gateway:
   ```bash
   node server.js
   ```

### 4. Conectando um WhatsApp
Para simular um cliente (clínica):
1. Peça a inicialização da sessão:
   ```bash
   curl -X POST http://localhost:3000/session/connect/clinica_teste
   ```
2. O QR Code aparecerá no terminal onde o Node.js está rodando. Escaneie com seu WhatsApp.
3. Verifique o status:
   ```bash
   curl http://localhost:3000/session/status/clinica_teste
   ```

### 5. Dashboard
Inicie o painel de controle:
```bash
streamlit run src/dashboard.py
```

## Estrutura de Dados
- **SQLite**: `data/sessions.db` (Python) e `whatsapp-gateway/whatsapp_auth.db` (Node.js).
- **JSON**: `data/mock_db.json` (Resultados de exames, isolados por `clientId`).
