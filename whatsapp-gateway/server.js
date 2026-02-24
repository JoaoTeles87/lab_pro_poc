const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage, Browsers, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const express = require('express');
const bodyParser = require('body-parser');
const pino = require('pino');
const axios = require('axios');
const cors = require('cors');
const qrcode = require('qrcode-terminal');

// CONFIGURAÇÕES
const PORT = process.env.PORT || 3000;
const BACKEND_WEBHOOK_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000/webhook';

const app = express();
app.use(cors());
app.use(bodyParser.json());

let isReconnecting = false;
let sock;

async function connectToWhatsApp() {
    if (isReconnecting) return;
    isReconnecting = true;

    console.log('🔄 Iniciando conexão com WhatsApp...');

    // CLOSE OLD SOCKET IF EXISTS
    if (sock && sock.ws) {
        try {
            sock.ev.removeAllListeners();
            sock.ws.close();
        } catch (e) {
            console.error("Erro ao fechar socket antigo:", e.message);
        }
    }

    const { state, saveCreds } = await useMultiFileAuthState('auth_info_v3');
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`🌐 Usando WhatsApp v${version.join('.')}, latest: ${isLatest}`);

    const logger = pino({ level: 'silent' });

    sock = makeWASocket({
        version,
        logger: logger,
        auth: state,
        syncFullHistory: false,
        printQRInTerminal: false,
        browser: Browsers.macOS('Desktop')
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('⚠️ ESCANEIE O QR CODE ABAIXO:');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect.error?.output?.statusCode;
            const errorMsg = lastDisconnect.error?.message || "";
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

            console.log(`❌ Conexão fechada. Status: ${statusCode}. Erro: ${errorMsg}`);

            // Detailed Trace for 405
            if (statusCode === 405) {
                console.error('🔍 Detalhes do Erro 405:', JSON.stringify(lastDisconnect.error, null, 2));
            }

            // FATAL ERROR CHECK: Bad MAC usually means corrupted session
            if (errorMsg.includes('Bad MAC') || errorMsg.includes('encryption')) {
                console.error('🛑 ERRO FATAL: Sessão corrompida (Bad MAC).');
                console.error('👉 AÇÃO NECESSÁRIA: Apague a pasta auth_info_v2 na VPS e reinicie o gateway.');
                isReconnecting = false;
                process.exit(1); // Exit to let PM2 restart or stop for manual fix
            }

            if (shouldReconnect) {
                console.log('⏳ Tentando reconectar em 10s...');
                setTimeout(() => {
                    isReconnecting = false;
                    connectToWhatsApp();
                }, 10000);
            } else {
                console.log('🚪 Deslogado. Não irá reconectar automaticamente.');
                isReconnecting = false;
            }
        } else if (connection === 'open') {
            console.log('✅ Gateway WhatsApp Conectado e Pronto!');
            isReconnecting = false;
        }
    });

    sock.ev.on('creds.update', saveCreds);


    const lidMap = new Map();
    const nameMap = new Map();

    sock.ev.on('contacts.upsert', (contacts) => {
        for (const contact of contacts) {
            // Mapear LID -> JID
            if (contact.lid && contact.id) {
                lidMap.set(contact.lid, contact.id);
            }
            // Mapear JID/LID -> Nome (notify ou name)
            const bestName = contact.name || contact.notify;
            if (bestName) {
                if (contact.id) nameMap.set(contact.id, bestName);
                if (contact.lid) nameMap.set(contact.lid, bestName);
            }
        }
    });

    sock.ev.on('creds.update', saveCreds);

    // ESCUTA MENSAGENS E MANDA PRO SEU BACKEND (PYTHON)
    sock.ev.on('messages.upsert', async m => {
        try {
            const msg = m.messages[0];

            // IGNORE OLD MESSAGES (Prevent Spam on Reconnect)
            // If message is older than 10 seconds, ignore.
            const msgTime = msg.messageTimestamp;
            const now = Math.floor(Date.now() / 1000);
            if (msgTime && (now - msgTime > 10)) {
                // Silently skip old history
                return;
            }

            // IGNORE STATUS UPDATES (Broadcasts)
            if (msg.key.remoteJid === 'status@broadcast') {
                console.log(`⚠️ Ignorando Status Update de: ${msg.key.participant}`);
                return;
            }

            // IGNORE SYSTEM MESSAGES (Encryption change, Group Add, Revoke, etc)
            if (msg.messageStubType) {
                console.log(`⚠️ Ignorando System Message (Stub): ${msg.messageStubType}`);
                return;
            }

            if (!msg.key.fromMe && m.type === 'notify') {

                // DETECT MESSAGE TYPE (Allowlist Strategy)
                const messageContent = msg.message;
                const allowedTypes = ['conversation', 'extendedTextMessage', 'imageMessage', 'documentMessage', 'audioMessage'];

                // Find which type matches
                const msgType = Object.keys(messageContent).find(key => allowedTypes.includes(key));

                if (!msgType) {
                    console.log(`⚠️ Ignorando tipo de mensagem desconhecido/sistema: ${Object.keys(messageContent).join(', ')}`);
                    return;
                }

                let text = msg.message?.conversation || msg.message?.extendedTextMessage?.text || msg.message?.imageMessage?.caption || "";
                let audioBase64 = null;

                // Handle Audio
                if (msg.message?.audioMessage) {
                    try {
                        console.log("🎤 Audio detectado. Baixando...");
                        const buffer = await downloadMediaMessage(
                            msg,
                            'buffer',
                            {},
                            {
                                logger: logger,
                                reuploadRequest: sock.updateMediaMessage
                            }
                        );
                        audioBase64 = buffer.toString('base64');
                        console.log("🎤 Audio baixado e convertido.");
                    } catch (dErr) {
                        console.error("❌ Falha ao baixar audio:", dErr);
                    }
                }

                // Detect Media Type
                const isImage = !!msg.message?.imageMessage;
                const isDocument = !!msg.message?.documentMessage;
                const isAudio = !!audioBase64;

                let mediaType = 'text';
                if (isAudio) mediaType = 'audio';
                else if (isImage) mediaType = 'image';
                else if (isDocument) mediaType = 'document';

                // STRICT FILTER: Ignore Status Updates / Polls / Empty Events
                // If text is empty AND it is not a recognized media, SKIP.
                if (!text && mediaType === 'text') {
                    console.log(`⚠️ Ignorando evento vazio (Status/Poll): ${msg.key.remoteJid}`);
                    return;
                }

                // Tenta resolver o JID real (Evita IDs @lid)
                // IMPROVED MAPPING LOGIC
                let effectiveJid = msg.key.remoteJid; // Default to remoteJid

                if (msg.key.remoteJidAlt) {
                    effectiveJid = msg.key.remoteJidAlt;
                } else if (lidMap.has(msg.key.remoteJid)) {
                    effectiveJid = lidMap.get(msg.key.remoteJid);
                } else if (msg.key.remoteJid.includes('@lid') && msg.key.participant && msg.key.participant.includes('@s.whatsapp.net')) {
                    effectiveJid = msg.key.participant;
                }

                // Tenta recuperar o NOME DA LISTA DE CONTATOS
                const contactName = nameMap.get(effectiveJid) || nameMap.get(msg.key.remoteJid);

                console.log(`🔑 Key Debug: Remote=${msg.key.remoteJid} => Resolvido: ${effectiveJid} (LID Map: ${lidMap.size})`);

                const payload = {
                    remoteJid: effectiveJid,
                    contactName: contactName,
                    pushName: msg.pushName,
                    text: text,
                    audio: audioBase64,
                    mediaType: mediaType,
                    timestamp: msg.messageTimestamp,
                    originalMessage: msg
                };

                // FIX: payload.text might be empty if audio only
                let display = text ? text.substring(0, 50) : '[Audio Message]';
                console.log(`📩 Enviando para LangGraph: ${display}`);

                try {
                    // Posta no seu backend Python
                    await axios.post(BACKEND_WEBHOOK_URL, payload);
                } catch (err) {
                    console.error(`❌ Erro ao contatar backend Python: ${err.message}`);
                }
            }
        } catch (error) {
            // Secure Logging: Don't dump full objects to avoid printing keys/buffers
            console.error("❌ Error processing message:", error.message || String(error));
        }
    });
}

// ROTA PARA SEU BACKEND ENVIAR MENSAGENS (Substitui a API do Evolution)
app.post('/send-message', async (req, res) => {
    const { number, text } = req.body;
    console.log(`📥 Recebido pedido de envio para: ${number}`);

    if (!sock) {
        console.error("❌ Erro: Sock não inicializado");
        return res.status(500).json({ error: 'WhatsApp não conectado' });
    }

    try {
        // Formata número se necessário (ex: garante o sufixo @s.whatsapp.net)
        // number comes usually as "5581..." without suffix from Replier
        const jid = number.includes('@') ? number : `${number}@s.whatsapp.net`;
        console.log(`🚀 Tentando enviar para: ${jid}`);

        await sock.sendMessage(jid, { text: text });
        console.log(`📤 Respondido para ${number}`);
        res.json({ status: 'sent' });
    } catch (error) {
        console.error("❌ Send Error:", error.message);
        // Clean error response
        res.status(500).json({ error: 'Falha ao enviar', details: error.message || String(error) });
    }
});

// INICIALIZAÇÃO
app.listen(PORT, () => {
    console.log(`🚀 Gateway rodando na porta ${PORT}`);
    connectToWhatsApp();
});
