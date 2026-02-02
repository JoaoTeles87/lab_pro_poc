# POC: Assistente Virtual Laboratório Pró-Análise
**Status Atual**: ✅ Funcional / Pronto para Demonstração

Este documento detalha as funcionalidades implementadas na Prova de Conceito (POC) e o roteiro de evoluções técnicas para o produto final.

---

## 🚀 Funcionalidades Implementadas (O que já funciona)

### 1. Arquitetura Híbrida Leve
- **Gateway WhatsApp Próprio**: Substituímos soluções pesadas (Evolution API via Docker) por um *Micro-Gateway Node.js* nativo.
    - **Benefício**: Roda em qualquer PC Windows simples (consumo < 100MB RAM), sem necessidade de servidores caros.
    - **Conexão**: QR Code direto no terminal, reconexão automática.

### 2. Inteligência Conversacional & Triagem
- **Menu Dinâmico**: Navegação por números ("1", "2"...) ou linguagem natural ("quero resultado", "ver orçamento").
- **Correção de Erros (Typos)**: Entende "Bradoesco" como "Bradesco", "Sassep" como "Sassepe", etc.
- **Fluxos de Estado (State Machine)**:
    - O robô "lembra" onde o usuário parou (ex: se pediu orçamento, sabe que a próxima resposta é o plano de saúde).
    - **Reset Automático**: Se o usuário sumir por 5 minutos, a conversa reinicia no Menu Principal automaticamente na próxima interação.

### 3. Suporte a Áudio (Transkription)
- **Áudios no WhatsApp**: O paciente pode falar o que quer.
- **Processamento**: O sistema baixa, converte e transcreve o áudio para texto localmente usando *Whisper*.
- **Ação**: O texto transcrito é processado como se fosse digitado (ex: áudio dizendo "quero meu resultado" aciona o menu de resultados).

### 4. Simulação de LIS (Sistema de Laboratório)
- **Mock DB**: Implementamos um banco de dados simulado (`data/mock_db.json`) para demonstrar integração real.
- **Consulta de Resultados**: O paciente digita o Protocolo/CPF e o sistema busca os exames, status (Pronto/Em Análise) e responde em tempo real.

### 5. Handoff Humano Inteligente
- **Modo Silencioso**: Quando a conversa requer um humano (ex: análise de foto de pedido), o robô entra em status `AGUARDANDO_HUMANO` e para de responder, permitindo que a atendente use o WhatsApp Web sem interferência.

---

## 🔮 Roadmap: Melhorias para Contrato Final

Para transformar essa POC no produto oficial do Laboratório, sugerimos as seguintes evoluções:

### Fase 1: Integração Real
- [ ] **Conexão com LIS Real**: Substituir o `mock_db.json` por chamadas API ao sistema do laboratório (ex: SmartLab, Shift, Matrix).
- [ ] **Envio de PDFs**: Enviar o PDF do laudo automaticamente quando o exame estiver "PRONTO".

### Fase 2: Robustez & Escala
- [ ] **Banco de Dados Real**: Migrar de `sessions.json` para SQLite ou PostgreSQL para maior segurança dos dados.
- [ ] **Dashboard de Atendimento**: Criar uma tela web simples para as atendentes verem quem está na fila do robô.
- [ ] **Filas Múltiplas**: Separar atendentes de "Orçamento" das de "Agendamento".

### Fase 3: IA Generativa (Opcional)
- [ ] **LLM Local/Cloud**: Usar GPT-4 ou LocalLLM para responder dúvidas médicas simples (ex: "Jejum para hemograma é de quantas horas?").

---

## 🛠️ Guia Rápido de Demonstração

1. **Iniciar Gateway**: `cd whatsapp-gateway` -> `node server.js`
2. **Iniciar Cérebro**: `python src/main.py`
3. **Cenários de Teste**:
    - *Áudio*: "Quero ver meu resultado" -> Digitar `123456`.
    - *Texto*: "Orçamento" -> "Unimed" -> (Mandar Foto).
    - *Reset*: Esperar 5 min após o handoff e mandar "Oi".
