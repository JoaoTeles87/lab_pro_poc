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
*Aguarde a mensagem "Whisper model loaded successfully".*

## Verificação
1.  Envie uma mensagem ("Oi") para o número conectado.
    -   O terminal Node deve mostrar: `📩 Enviando para LangGraph: Oi`
    -   O terminal Python deve mostrar: `[IN/GW] Msg from ...: Oi` e responder com o Menu.
2.  Teste um Áudio.
    -   O terminal Node deve mostrar: `🎤 Audio detectado. Baixando...`
    -   O terminal Python deve mostrar: `[TRANS] <texto transcrito>`

## Notas
-   O arquivo de sessão do WhatsApp fica salvo em `whatsapp-gateway/auth_info`.
-   Para reiniciar sem pedir QR Code, basta rodar `node server.js` novamente.
-   Para limpar a sessão e ler QR Code novo: apague a pasta `auth_info`.
