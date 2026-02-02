# Changelog - Lab Pró-Análise POC

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
