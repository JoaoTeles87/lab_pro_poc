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
            node_args: "--max-old-space-size=1024",
            max_memory_restart: "800M",
            env: {
                PORT: 3000,
                BACKEND_URL: "http://127.0.0.1:8000/webhook"
            }
        },
        {
            name: "lab-dashboard",
            script: "./.venv/bin/python3",
            args: "-m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0",
            cwd: "./",
            env: {
                PYTHONPATH: ".",
                DASHBOARD_PASSWORD: "lab123"
            }
        }
    ]
};
