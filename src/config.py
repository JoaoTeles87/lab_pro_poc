import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 8000))
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "host.docker.internal")

# Calculated URLs
WEBHOOK_URL = f"http://{WEBHOOK_HOST}:{PORT}/webhook/evolution"
