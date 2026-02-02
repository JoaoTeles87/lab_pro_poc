import os
import uvicorn

# Add FFmpeg to PATH (Must be before imports that use it)
os.environ["PATH"] += os.pathsep + r"D:\Projetos\lab_pro_poc\ffmpeg\bin"

from src.api.webhook import app
from src.config import PORT

if __name__ == "__main__":
    # Running on port from config
    uvicorn.run(app, host="0.0.0.0", port=PORT)
