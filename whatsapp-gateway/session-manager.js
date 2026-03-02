const { default: makeWASocket, DisconnectReason, fetchLatestBaileysVersion, Browsers } = require('@whiskeysockets/baileys');
const { useSQLiteAuthState } = require('./db-auth');
const axios = require('axios');
const pino = require('pino');

const IDLE_TIMEOUT = 10 * 60 * 1000; // 10 minutes
const RECONNECT_DELAY = 10000;

class SessionManager {
    constructor(webhookUrl) {
        this.webhookUrl = webhookUrl;
        this.sessions = new Map(); // clientId -> { sock, lastActivity, status }
        this.logger = pino({ level: 'silent' });

        // Start idle checker
        setInterval(() => this.checkIdleSessions(), 60000);
    }

    async getSock(clientId, autoConnect = true) {
        let session = this.sessions.get(clientId);

        if (!session && autoConnect) {
            return await this.initSession(clientId);
        }

        if (session && !session.sock && autoConnect) {
            return await this.initSession(clientId);
        }

        return session ? session.sock : null;
    }

    async initSession(clientId) {
        console.log(`[SESSION] Initializing: ${clientId}`);
        const { state, saveCreds, clearState } = useSQLiteAuthState(clientId);
        const { version } = await fetchLatestBaileysVersion();

        const sock = makeWASocket({
            version,
            logger: this.logger,
            auth: state,
            printQRInTerminal: false,
            browser: Browsers.macOS('Desktop'),
            syncFullHistory: false,
        });

        const session = {
            sock,
            status: 'connecting',
            lastActivity: Date.now(),
            clearState,
            qr: null,
            botSentIds: new Set()
        };

        this.sessions.set(clientId, session);

        sock.ev.on('connection.update', (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                console.log(`[SESSION] [${clientId}] QR Received`);
                session.qr = qr;
            }

            if (connection === 'open') {
                console.log(`[SESSION] [${clientId}] Connected`);
                session.status = 'open';
                session.qr = null;
                session.lastActivity = Date.now();
            }

            if (connection === 'close') {
                const statusCode = lastDisconnect.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

                // 4005 is a common code for intentional close, or when we call ws.close() it might be undefined
                const isIdleDisconnect = session.status === 'idle';

                console.log(`[SESSION] [${clientId}] Disconnected. Status: ${statusCode}. Idle: ${isIdleDisconnect}`);

                if (statusCode === DisconnectReason.loggedOut) {
                    console.log(`[SESSION] [${clientId}] Logged out by user. Deleting session.`);
                    this.deleteSession(clientId);
                } else if (shouldReconnect && !isIdleDisconnect) {
                    console.log(`[SESSION] [${clientId}] Unexpected drop. Auto-reconnecting in 2s...`);
                    session.sock = null;
                    session.status = 'closed';
                    setTimeout(() => {
                        this.initSession(clientId).catch(e => console.error(`[SESSION] [${clientId}] Reconnect failed:`, e));
                    }, 2000);
                } else {
                    console.log(`[SESSION] [${clientId}] Graceful/Idle disconnect. Standing by.`);
                    session.sock = null;
                    // Keep status as idle or closed
                }
            }
        });

        sock.ev.on('creds.update', saveCreds);

        sock.ev.on('messages.upsert', async m => {
            session.lastActivity = Date.now();
            const msg = m.messages[0];
            if (!msg.message) return;

            // Basic filtering already done in server.js, but let's relay the core info
            this.handleInbound(clientId, m);
        });

        return sock;
    }

    async handleInbound(clientId, m) {
        try {
            const msg = m.messages[0];
            const fromMe = msg.key.fromMe;
            const session = this.sessions.get(clientId);

            // Se for do própio bot enviado via API, ignorar! Não é humano.
            if (fromMe && session?.botSentIds?.has(msg.key.id)) {
                // Ignore our own api-sent messages
                session.botSentIds.delete(msg.key.id); // remove to save memory
                return;
            }

            // Simple relay to Python
            const payload = {
                clientId,
                remoteJid: msg.key.remoteJid,
                pushName: msg.pushName,
                text: msg.message?.conversation || msg.message?.extendedTextMessage?.text || "",
                fromMe: !!fromMe,
                mediaType: Object.keys(msg.message)[0],
                timestamp: msg.messageTimestamp
            };

            await axios.post(this.webhookUrl, payload);
        } catch (e) {
            console.error(`[SESSION] [${clientId}] Webhook Error: ${e.message}`);
        }
    }

    async sendMessage(clientId, jid, text) {
        const sock = await this.getSock(clientId);
        if (!sock) throw new Error('Session not found or failed to initialize');

        // Wait for connection if still connecting
        let attempts = 0;
        while (this.sessions.get(clientId).status !== 'open' && attempts < 10) {
            await new Promise(r => setTimeout(r, 1000));
            attempts++;
        }

        if (this.sessions.get(clientId).status !== 'open') {
            throw new Error('Timeout waiting for connection');
        }

        const result = await sock.sendMessage(jid, { text });

        // Track the message ID so we don't treat it as "human handoff" when it bounces back
        const session = this.sessions.get(clientId);
        if (result && result.key && result.key.id) {
            session.botSentIds = session.botSentIds || new Set();
            session.botSentIds.add(result.key.id);

            // Prevent memory leak if upsert never comes (e.g., Baileys glitch)
            setTimeout(() => session.botSentIds.delete(result.key.id), 60000);
        }

        session.lastActivity = Date.now();
        return result;
    }

    async checkIdleSessions() {
        const now = Date.now();
        for (const [clientId, session] of this.sessions.entries()) {
            if (session.sock && session.status === 'open') {
                if (now - session.lastActivity > IDLE_TIMEOUT) {
                    console.log(`[IDLE] Disconnecting session: ${clientId} to save RAM`);
                    try {
                        session.sock.ws.close();
                        session.sock = null;
                        session.status = 'idle';
                    } catch (e) {
                        console.error(`[IDLE] Error closing ${clientId}: ${e.message}`);
                    }
                }
            }
        }
    }

    deleteSession(clientId) {
        const session = this.sessions.get(clientId);
        if (session) {
            if (session.sock) session.sock.ws.close();
            if (session.clearState) session.clearState();
            this.sessions.delete(clientId);
            console.log(`[SESSION] [${clientId}] Deleted and Logged out`);
        }
    }

    getStatus(clientId) {
        const session = this.sessions.get(clientId);
        if (!session) return { status: 'not_found' };
        return {
            status: session.status,
            lastActivity: session.lastActivity,
            qr: !!session.qr
        };
    }
}

module.exports = SessionManager;
