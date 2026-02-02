import whisper
import os

# Global model loading to avoid overhead per request
# User suggested 'base' model for Portuguese/Latam context efficiency
MODEL_SIZE = "small"
MODEL_SIZE = "small"
# [HIBERNATION MODE]
# model = whisper.load_model(MODEL_SIZE)
model = None # Disable for OCI Micro

class Transcriber:
    def __init__(self):
        import shutil
        if not shutil.which("ffmpeg"):
            print("WARNING: FFmpeg not found in PATH. Audio transcription will fail.")
        
        if model is None:
            raise RuntimeError("Whisper model failed to load.")

    def transcribe_audio(self, file_path: str) -> str:
        """
        Transcribes the audio file at the given path.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        try:
            # Enforce Portuguese and use initial_prompt for domain context
            result = model.transcribe(
                file_path, 
                language="pt",
                initial_prompt="Laboratório, Exame, Unimed, Bradesco, Saúde, Sassepe, Geap, Orçamento, Resultado, Hemograma, Glicose, Coleta"
            )
            return result["text"].strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            raise e
