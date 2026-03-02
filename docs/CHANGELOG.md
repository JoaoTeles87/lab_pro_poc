# Changelog - Lab Pró-Análise POC

## [SaaS Multitenancy & Gateway Otimizações] - 2026-02-26

### 🚀 Novas Funcionalidades
- **Arquitetura Multiclínicas (SaaS)**: O backend e o gateway agora suportam múltiplas clínicas operando na mesma infraestrutura através da segregação por `client_id` (Chaves Compostas no SQLite).
- **Dashboard Multitenant**: O painel de controle agora possui um seletor de clínicas na barra lateral para monitoramento isolado.

### 🛠 System & Infrastructure
- **Gateway SQLite Auth**: Substituído o armazenamento de credenciais em vários arquivos soltos (`auth_info`) por um banco único de alta performance (`whatsapp_auth.db`) usando `better-sqlite3`.
- **Idle Disconnect**: O Gateway Node.js agora fecha o socket ativo do WhatsApp após 10 minutos de inatividade para poupar memória na VPS, reconectando automaticamente ("Sob Demanda") apenas quando novas mensagens chegam ou no envio reativo.
- **Python Timeout Resilience**: O Backend agora está preparado com timeout de 20s para aguardar a reconexão automática do Gateway.
- **Bot Echo Filter**: Implementado um cache em memória no Gateway (`botSentIds`) para ignorar as mensagens enviadas pela própria API, evitando o falso gatilho de *Human Handoff*.

## [Latest Refinements] - 2026-01-31

### 🧠 Logic & Flow Improvements
- **Smart Handoff (Long Messages in Menu)**
  - **Behavior**: Messages > 60 chars without clear intent triggers immediate human handoff.
  - **Goal**: Prevent menu loops when users send complex queries or "textões".

- **Smart Handoff (Registration Phase)**
  - **Behavior**: Messages > 50 chars during "Ask Name" are **not** saved as the name.
  - **Action**: Transitions to `AGUARDANDO_HUMANO` with the name field left empty (waiting for contact sync).
  - **Goal**: Prevent saving long audios/texts as "Obrigado, [Text]!" and ensures complex greetings go to support.

- **Results & Payment Proof**
  - **Flow Update**: "Resultados" intent now asks for **Comprovante/Foto**.
  - **Action**: Any input (Photo/Text) in this state transitions to `AGUARDANDO_HUMANO` for verification.
  - **Goal**: Enforce payment check before releasing results.

- **Terminology: Particular vs. Sem Plano**
  - **Update**: Bot prompts now ask for "Pagamento à vista/sem plano" instead of just "Particular".
  - **Keywords**: Added `dinheiro`, `pix`, `sem plano` to Triage.

### 🛠 System & Infrastructure
- **Audio Hibernation**: Disabled Whisper model loading to save resources (VPS ready).
- **Global Audio Handoff**: All audio in Menu redirects to Human.
- **Advanced Triage**: Implemented Regex for URL removal and elongation fix (`triage.py`).
- **Safety Fixes**: Fixed correct name preservation on Timeout/Reset.
- **Dashboard UI**: Now displays **Patient Name** (e.g., "👤 João Doe") instead of just Phone Number when available.
