const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const qrcode = require('qrcode-terminal');
const SessionManager = require('./session-manager');

// CONFIGURAÇÕES
const PORT = process.env.PORT || 3000;
const BACKEND_WEBHOOK_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000/webhook';

const app = express();
app.use(cors());
app.use(bodyParser.json());

const manager = new SessionManager(BACKEND_WEBHOOK_URL);

// --- ROTAS DE GERENCIAMENTO ---

// Inicializar/Conectar uma clínica
app.post('/session/connect/:clientId', async (req, res) => {
    const { clientId } = req.params;
    try {
        await manager.getSock(clientId, true);
        res.json({ status: 'initializing', clientId });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Obter QR Code (Terminal e JSON)
app.get('/session/qr/:clientId', (req, res) => {
    const { clientId } = req.params;
    const session = manager.sessions.get(clientId);

    if (!session || !session.qr) {
        return res.status(404).json({ error: 'QR not available or session connected' });
    }

    // Print to terminal for debugging
    qrcode.generate(session.qr, { small: true });

    res.json({ qr: session.qr });
});

// Status da conexão
app.get('/session/status/:clientId', (req, res) => {
    const { clientId } = req.params;
    res.json(manager.getStatus(clientId));
});

// Logout / Excluir sessão
app.delete('/session/logout/:clientId', (req, res) => {
    const { clientId } = req.params;
    manager.deleteSession(clientId);
    res.json({ status: 'deleted', clientId });
});

// --- ROTA DE ENVIO ---

app.post('/send-message/:clientId', async (req, res) => {
    const { clientId } = req.params;
    const { number, text } = req.body;

    if (!number || !text) {
        return res.status(400).json({ error: 'Faltando number ou text' });
    }

    try {
        const jid = number.includes('@') ? number : `${number}@s.whatsapp.net`;
        console.log(`[OUT] [${clientId}] Sending to ${jid}`);

        await manager.sendMessage(clientId, jid, text);
        res.json({ status: 'sent' });
    } catch (error) {
        console.error(`[ERROR] [${clientId}] Send Error:`, error.message);
        res.status(500).json({ error: 'Falha ao enviar', details: error.message });
    }
});

// BC Compatibility
app.post('/send-message', async (req, res) => {
    res.status(400).json({ error: 'Use /send-message/:clientId' });
});

// INICIALIZAÇÃO
app.listen(PORT, () => {
    console.log(`🚀 Gateway Multitenant rodando na porta ${PORT}`);
    console.log(`🔗 Webhook configurado para: ${BACKEND_WEBHOOK_URL}`);
});
