# Guia de Deploy e Execução Contínua

Este guia aborda como manter o **Lab Pró-Análise Bot** rodando 24/7 e como evitar quedas de conexão.

## 1. O Problema da Suspensão (Notebooks)
Quando você fecha a tampa do notebook ou ele entra em modo de suspensão (Sleep):
1.  O **Processador** para.
2.  A **Placa de Rede** desliga.
3.  O **Docker/Node/Python** são congelados.

Consequência: O Gateway do WhatsApp perde a conexão e o backend para de responder.

## 2. Solução para Desenvolvimento (Local)
Para evitar que isso ocorra enquanto você está testando ou usando localmente:

### Opção A: Ajustar Energia (Windows)
1.  Abra **Painel de Controle** > **Opções de Energia**.
2.  Escolha o plano **Alto Desempenho**.
3.  Clique em **Alterar configurações do plano**.
4.  Em "Suspender atividade do computador", selecione **Nunca** (pelo menos quando conectado à tomada).
5.  Em "Fechamento da tampa" (opções avançadas), configure para **Nada a fazer**.

### Opção B: PowerToys Awake
Se você usa o Microsoft PowerToys, use a ferramenta **Awake** (ícone de xícara de café) para manter o PC acordado sem alterar as configurações globais.

---

## 3. Solução para Produção (Definitiva)
Para um bot de WhatsApp profissional, não recomendamos rodar em um notebook pessoal. A solução ideal é usar um **Servidor Virtual (VPS)**.

### Arquitetura Recomendada
*   **Servidor**: Ubuntu 22.04 LTS (AWS EC2, DigitalOcean Droplet, Hetzner, etc.).
*   **Custo Estimado**: ~$5-10 USD/mês.
*   **Banco de Dados**: Em vez de `sessions.json`, usaríamos um banco real (PostgreSQL ou redis) para persistência segura. É aqui que o **LangGraph** brilha, gerenciando o estado da conversa no banco.

### Passos para Deploy (Resumo)
1.  **Contratar VPS**: Criar uma máquina Linux.
2.  **Instalar Docker**: `apt install docker.io`.
3.  **Transferir Código**: Git clone do seu repositório.
4.  **Rodar Background**: Usar `docker compose up -d` ou gerenciadores de processo como `PM2` (Node) e `Systemd` (Python).

Isso garante que o bot funcione 24 horas por dia, 7 dias por semana, sem depender da bateria ou da tampa do seu notebook.
