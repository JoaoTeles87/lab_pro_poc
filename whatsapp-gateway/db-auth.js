const Database = require('better-sqlite3');
const { proto, BufferJSON, initAuthCreds } = require('@whiskeysockets/baileys');

function useSQLiteAuthState(clientId, dbPath = './whatsapp_auth.db') {
    const db = new Database(dbPath);

    // Initialize tables
    db.prepare(`
        CREATE TABLE IF NOT EXISTS sessions (
            clientId TEXT PRIMARY KEY,
            creds TEXT
        )
    `).run();

    db.prepare(`
        CREATE TABLE IF NOT EXISTS keys (
            clientId TEXT,
            type TEXT,
            id TEXT,
            data TEXT,
            PRIMARY KEY (clientId, type, id)
        )
    `).run();

    const writeData = (data, type, id) => {
        const json = JSON.stringify(data, BufferJSON.replacer);
        db.prepare('INSERT OR REPLACE INTO keys (clientId, type, id, data) VALUES (?, ?, ?, ?)').run(clientId, type, id, json);
    };

    const readData = (type, id) => {
        const row = db.prepare('SELECT data FROM keys WHERE clientId = ? AND type = ? AND id = ?').get(clientId, type, id);
        return row ? JSON.parse(row.data, BufferJSON.reviver) : null;
    };

    const removeData = (type, id) => {
        db.prepare('DELETE FROM keys WHERE clientId = ? AND type = ? AND id = ?').run(clientId, type, id);
    };

    const clearKeys = () => {
        db.prepare('DELETE FROM keys WHERE clientId = ?').run(clientId);
    };

    // Load initial creds
    const row = db.prepare('SELECT creds FROM sessions WHERE clientId = ?').get(clientId);
    let creds = row ? JSON.parse(row.creds, BufferJSON.reviver) : initAuthCreds();

    return {
        state: {
            creds,
            keys: {
                get: async (type, ids) => {
                    const data = {};
                    await Promise.all(
                        ids.map(async (id) => {
                            let value = await readData(type, id);
                            if (type === 'app-state-sync-key' && value) {
                                value = proto.Message.AppStateSyncKeyData.fromObject(value);
                            }
                            data[id] = value;
                        })
                    );
                    return data;
                },
                set: async (data) => {
                    for (const type in data) {
                        for (const id in data[type]) {
                            const value = data[type][id];
                            if (value) {
                                await writeData(value, type, id);
                            } else {
                                await removeData(type, id);
                            }
                        }
                    }
                }
            }
        },
        saveCreds: () => {
            const json = JSON.stringify(creds, BufferJSON.replacer);
            db.prepare('INSERT OR REPLACE INTO sessions (clientId, creds) VALUES (?, ?)').run(clientId, json);
        },
        clearState: () => {
            db.prepare('DELETE FROM sessions WHERE clientId = ?').run(clientId);
            clearKeys();
        }
    };
}

module.exports = { useSQLiteAuthState };
