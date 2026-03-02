# Nova Arquitetura WhatsApp (Sem Docker)

## Resumo das Mudanças
Substituímos o Evolution API (Docker) por um **Gateway Node.js** leve usando a biblioteca Baileys. Isso reduz drasticamente o consumo de recursos (3GB -> 60MB).

### Componentes:
1.  **WhatsApp Gateway (Node.js)**: 
    -   Porta: `3000`
    -   Função: Conecta ao WhatsApp, recebe mensagens/áudio e envia para o Python.
    -   Dependências: `express`, `baileys`, `pino`, `qrcode-terminal`.
2.  **Backend Agêntico (Python)**:
    -   Porta: `8000`
    -   Função: Processa a lógica (LangGraph/Ontologia), transcreve áudio (Whisper + FFmpeg) e gerencia sessões.
    -   Dependência Externa: `FFmpeg` (configurado em `d:\Projetos\lab_pro_poc\ffmpeg`).

## Como Rodar

### Passo 1: Iniciar o Gateway WhatsApp
No terminal do Windows (Powershell):
```bash
cd whatsapp-gateway
node server.js
```
*Aguarde o QR Code aparecer no terminal e escaneie com seu WhatsApp.*

### Passo 2: Iniciar o Backend Python
Em **outro** terminal:
```bash
# Se necessário, ative o ambiente virtual
# .venv\Scripts\activate
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Passo 3: Conectar uma Clínica (Multitenancy)
Como o sistema agora suporta múltiplas clínicas simultâneas, você precisa iniciar a sessão via API informando o `clientId`:

No terminal antigo (ou em um terceiro):
```bash
curl -X POST http://localhost:3000/session/connect/NOME_DA_CLINICA
```
*Aguarde o QR Code aparecer no terminal do Node.js e escaneie com seu WhatsApp.*

## Verificação
1.  Envie uma mensagem ("Oi") para o número conectado.
    -   O terminal Node deve mostrar a mensagem recebida.
    -   O terminal Python deve processar e responder "Olá!".
2.  Teste a reconexão automática:
    -   Aguarde 10 minutos de inatividade: o Node.js fará o **Idle Disconnect** (fechará o socket para poupar memória).
    -   Mande uma mensagem pelo celular de teste: o Node.js deve reconectar quase instantaneamente e entregar a mensagem ao Python.

## Notas
-   As credenciais do WhatsApp ficam salvas e centralizadas no banco **SQLite** em `whatsapp-gateway/whatsapp_auth.db`.
-   Para deslogar um cliente: `curl -X DELETE http://localhost:3000/session/logout/NOME_DA_CLINICA`
-   Para limpar TODAS as sessões de todos os clientes: apague o arquivo `whatsapp_auth.db`.
