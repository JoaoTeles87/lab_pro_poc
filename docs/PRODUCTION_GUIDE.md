# Production Guide - Lab Pró-Análise 🚀

## 1. Arquitetura "Bare Metal" (Recomendada)
Para sua instância **OCI Micro (1GB RAM)**, rodamos os serviços diretamente no OS para economizar a memória que o Docker consumiria.

### Stack
*   **Gateway**: Node.js (via PM2)
    *   *Otimização*: Utiliza "Idle Disconnect" para derrubar sockets inativos após 10min, economizando RAM. Autenticação via SQLite (`whatsapp-gateway/whatsapp_auth.db`).
*   **Backend**: Python FastAPI (via PM2)
*   **Banco de Dados**: **SQLite** (Arquivo `data/sessions.db`)
    *   *Multitenancy*: Usa chaves compostas (`client_id`, `phone`) para isolar diferentes clínicas rodando no mesmo processo.
*   **Dashboard**: Streamlit (via PM2)

## 2. Configurações de Produção
O código já foi ajustado para:
*   **Retenção**: Limpeza automática de sessões antigas (> **120 dias**).
*   **Sessão**: Timeout de **24 horas** (o robô mantém com contexto o dia todo).
*   **Performance**: Modelo de Áudio (Whisper) **Desativado** para caber na RAM.

## 3. Dashboard & Segurança
O Dashboard roda localmente lendo o SQLite.
*   **Autenticação**: Adicionada tela de login.
    *   Senha padrão: `lab123`
    *   Para mudar, defina a env var: `DASHBOARD_PASSWORD=SuaSenhaForte`

### Deploy do Dashboard (Vercel vs VPS)
**Pergunta**: *Posso usar Vercel?*
**Resposta**: **Não diretamente**, pois o Dashboard precisa ler o arquivo `sessions.db` que está salvo no disco da sua VPS. O Vercel não tem acesso a esse arquivo.

**Solução Recomendada (Nginx Reverse Proxy)**:
Para acessar o dashboard de forma profissional (`painel.seudominio.com`) sem abrir porta 8501:

1.  Instale Nginx: `sudo apt install nginx`
2.  Crie config `/etc/nginx/sites-available/dashboard`:
    ```nginx
    server {
        listen 80;
        server_name painel.seudominio.com;
        
        location / {
            proxy_pass http://127.0.0.1:8501;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
    ```

## 4. Passo-a-Passo de Instalação (OCI)

1.  **Acesse a VPS**: `ssh ubuntu@seu-ip`
2.  **Copie os Arquivos**: (Use `scp` ou `git clone`).
3.  **Execute o Instalador**:
    ```bash
    chmod +x install.sh
    ./install.sh
    ```
4.  **Verifique**: `pm2 status`
    *   Deve ver `lab-backend`, `lab-gateway` online.
    *   *Opcional*: Adicione o dashboard ao PM2: `pm2 start "uv run streamlit run src/dashboard.py" --name lab-dash`

## 5. Manutenção
*   **Backup**: Copie o arquivo `data/sessions.db` semanalmente.
*   **Logs**: `pm2 logs`
