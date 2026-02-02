module.exports = {
    apps: [
        {
            name: "lab-backend",
            script: "./.venv/bin/python3",
            args: "-m uvicorn src.main:app --host 127.0.0.1 --port 8000",
            cwd: "./",
            env: {
                PYTHONPATH: "."
            }
        },
        {
            name: "lab-gateway",
            script: "server.js",
            cwd: "./whatsapp-gateway",
            env: {
                PORT: 3000,
                BACKEND_URL: "http://127.0.0.1:8000/webhook"
            }
        }
    ]
};
