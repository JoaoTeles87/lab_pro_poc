const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage } = require('@whiskeysockets/baileys');
const express = require('express');
const bodyParser = require('body-parser');
const pino = require('pino');
const axios = require('axios');
const cors = require('cors');
const qrcode = require('qrcode-terminal');

// CONFIGURAÇÕES
const PORT = 3000; // Porta deste Gateway
const BACKEND_WEBHOOK_URL = 'http://127.0.0.1:8000/webhook'; // URL do seu Backend Python (LangGraph)

const app = express();
app.use(cors());
app.use(bodyParser.json());

let sock;

async function connectToWhatsApp() {
    // FORCE NEW SESSION - Avoids "Unsupported state" from corrupted old folder
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_v2');


    const logger = pino({ level: 'silent' });

    sock = makeWASocket({
        logger: logger,
        // printQRInTerminal: true, // DEPRECATED
        auth: state,
        // Necessário para chaves de criptografia (Self/LID)
        syncFullHistory: false // CRITICAL: Disabled to prevent spamming old chats
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('⚠️ ESCANEIE O QR CODE ABAIXO:');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const shouldReconnect = lastDisconnect.error?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('Connection closed. Reconnecting:', shouldReconnect);
            if (shouldReconnect) connectToWhatsApp();
        } else if (connection === 'open') {
            console.log('✅ Gateway WhatsApp Conectado e Pronto!');
        }
    });


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

            if (!msg.key.fromMe && m.type === 'notify') {

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

                // Allow processing if text exists OR if it's a known media type
                if (!text && mediaType === 'text') {
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

                console.log(`🔍 Diagnóstico LID: MapSize=${lidMap.size}`);
                console.log(`🔑 Key Debug: Remote=${msg.key.remoteJid} => Resolvido: ${effectiveJid}`);

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
