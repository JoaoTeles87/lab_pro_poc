from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests
import json
import os
import uuid
import base64
from src.core.triage import Triage
from src.core.transcriber import Transcriber
from src.core.session import SessionManager
from src.core.replier import Replier

app = FastAPI(title="Anti-Gravity Sprint Hook")

# Initialize cores
triage_service = Triage()
session_manager = SessionManager()
replier_service = Replier()

# Transcriber might fail if FFmpeg is missing, handle gracefully?
# For now, we instantiate on demand or let it fail at startup if model is None?
# The Transcriber checks global model at __init__. We'll instantiate it here.
# [HIBERNATION MODE] - Saving Resources for VPS
transcriber_service = None
# try:
#     transcriber_service = Transcriber()
# except Exception as e:
#     print(f"WARNING: Transcriber not available: {e}")
#     transcriber_service = None

import time

# ... (existing imports)

# Data directory (Force to D: to avoid ENOSPC on C:)
DATA_DIR = r"D:\Projetos\lab_pro_poc\data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def cleanup_old_files(directory: str, max_age_seconds: int = 3600):
    """
    Deletes .ogg files in the directory that are older than max_age_seconds (default 1h).
    """
    try:
        now = time.time()
        for filename in os.listdir(directory):
            if filename.endswith(".ogg"):
                file_path = os.path.join(directory, filename)
                # Check modification time
                if os.path.isfile(file_path):
                    mtime = os.path.getmtime(file_path)
                    if now - mtime > max_age_seconds:
                        os.remove(file_path)
                        print(f"   [CLEANUP] Deleted old file: {filename}")
    except Exception as e:
        print(f"   [CLEANUP] Error during cleanup: {e}")

class EvolutionPayload(BaseModel):
    event: str
    instance: str
    data: Dict[str, Any]
    destination: Optional[str] = None

class SimpleWhatsappPayload(BaseModel):
    remoteJid: str
    contactName: Optional[str] = None
    pushName: Optional[str] = None
    text: str
    audio: Optional[str] = None  # Base64 audio
    mediaType: Optional[str] = "text" # text, audio, image, document
    timestamp: Optional[Any] = None
    timestamp: Optional[Any] = None
    originalMessage: Optional[Dict[str, Any]] = None

@app.post("/webhook")
async def whatsapp_webhook(payload: SimpleWhatsappPayload):
    print(f"[IN/GW] Msg from {payload.remoteJid}: {payload.text}")
    
    sender = payload.remoteJid
    text_content = payload.text
    
    # Handle Audio
    if payload.audio:
        try:
             print("   [AUDIO] Processing audio from gateway...")
             
             # Run Cleanup (1 hour threshold)
             cleanup_old_files(DATA_DIR)

             # [HIBERNATION MODE] Skip Whisper
             print("   [HIBERNATION] Skipping transcription. Passing generic audio tag.")
             
             # Instead of decoding and transcribing, we just tag it.
             # The Session Logic (MENU_PRINCIPAL) handles 'media_type="audio"' by auto-handoff.
             text_content = "[AUDIO_RECEIVED]" 
             
             # Obsolete code in hibernation:
             # if not transcriber_service: ...
             # Decode Base64 ...
             # Transcribe ...
                 
        except Exception as e:
            print(f"   [ERROR] Audio processing failed: {e}")
            replier_service.send_text(sender, "Erro ao processar seu áudio. Pode escrever?")
            return {"status": "error", "reason": str(e)}

    
    
    if not text_content and payload.mediaType == "text":
        return {"status": "ignored", "reason": "no text"}

    # 3. Triage
    intent = triage_service.detect_intent(text_content)
    entities = triage_service.extract_entities(text_content)
    
    print(f"   [OUT] Intent: {intent} | Entities: {entities}")
    # 4. Update Session
    phone = sender.split("@")[0]
    
    session_result = session_manager.update_session(
        phone=phone,
        message=text_content,
        intent=intent,
        entities=entities,
        contact_name=payload.contactName or payload.pushName, # Prefer Contact, then Push
        media_type=payload.mediaType
    )
    print(f"   [SESSION] State: {session_result['status']}")
    
    # 5. Auto-Reply
    reply_msg = session_result.get("reply_message")
    if reply_msg:
        replier_service.send_text(sender, reply_msg)

    return {
        "status": "processed",
        "input": text_content,
        "intent": intent,
        "session": "updated"
    }

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """
    Receives events from Evolution API.
    Relaxed validation to debug 422 errors.
    """
    try:
        payload = await request.json()
    except Exception as e:
        print(f"FAILED to parse JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    print(f"RAW PAYLOAD: {json.dumps(payload, indent=2)}")

    # Adapting to variable payload structures
    event_type = payload.get("event")
    print(f"   [EVENT] {event_type}")

    if event_type != "messages.upsert":
        # We only care about new messages for now
        return {"status": "ignored", "reason": f"Event {event_type} not handled"}

    data = payload.get("data", {})
    
    # Safety check: data might be a list in some events, or dict in messages.upsert
    if isinstance(data, list):
        print(f"   [WARN] 'data' is a list for {event_type}. Ignoring.")
        return {"status": "ignored", "reason": "data is a list"}
    
    # If data is missing but message is top level
    if not data and "message" in payload:
        data = payload

    message = data.get("message", {})
    if not message:
         print("   [WARN] No message content found.")
         return {"status": "ignored", "reason": "no message content"}

    # Extract Sender ID

    # Evolution sends 'key': {'remoteJid': ...} inside data
    key = data.get("key", {})
    sender = key.get("remoteJid", "unknown")
    
    # Handle LID (Business Accounts) - prefer the real phone number if available
    # usually in 'remoteJidAlt' or we have to use the lid?
    # Evolution often provides 'remoteJidAlt' for LIDs
    if sender.endswith("@lid") and key.get("remoteJidAlt"):
        sender = key.get("remoteJidAlt")

    
    print(f"[IN] Msg from {sender}")

    text_content = ""
    intent = None
    entities = {}

    # 1. Handle Text
    if "conversation" in message and message["conversation"]:
        text_content = message["conversation"]
        print(f"   [TEXT] {text_content}")

    # 2. Handle Audio
    elif "audioMessage" in message:
        print("   [AUDIO] Processing...")
        if not transcriber_service:
            print("   [ERROR] Transcriber service unavailable.")
            return {"status": "error", "message": "Transcriber unavailable"}

        audio_msg = message["audioMessage"]
        # Basic Evolution API often sends a 'url' to download or base64. 
        # User mentioned "url para download ou o base64".
        # Let's try downloading from URL first if present.
        
        audio_url = audio_msg.get("url")
        # Ensure unique filename
        file_id = str(uuid.uuid4())
        file_path = os.path.join(DATA_DIR, f"{file_id}.ogg")

        try:
            # Prioritize Base64 (Evolution API setting)
            if "base64" in audio_msg:
                 # Decode base64
                 audio_data = base64.b64decode(audio_msg["base64"])
                 with open(file_path, "wb") as f:
                     f.write(audio_data)

            elif audio_url:
                # Check for likely encrypted WhatsApp URL
                if "mmg.whatsapp.net" in audio_url and ".enc" in audio_url:
                    print(f"   [WARN] Skipping encrypted WhatsApp URL: {audio_url}")
                    print("   [TIP] Enable 'include base64' in your Evolution API webhook settings for this instance.")
                    return {"status": "ignored", "reason": "encrypted url, base64 missing"}

                # Try Download (only if standard URL)
                response = requests.get(audio_url)
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(response.content)
            else:
                print("   [ERROR] No URL or Base64 in audio message.")
                return {"status": "ignored", "reason": "no audio data found"}
            
            # Check file size
            if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
                 print("   [ERROR] Downloaded audio file is empty.")
                 return {"status": "error", "reason": "empty audio file"}

            # Transcribe
            text_content = transcriber_service.transcribe_audio(file_path)
            print(f"   [TRANS] {text_content}")
            
            # Clean up file (optional? User didn't specify, but good practice for 'sprint')
            # os.remove(file_path)
            
        except Exception as e:
            print(f"   [ERROR] Audio processing failed: {e}")
            return {"status": "error", "reason": str(e)}

    else:
        # Ignore other types
        return {"status": "ignored", "reason": "not text or audio"}


    if text_content:
        # 3. Triage
        intent = triage_service.detect_intent(text_content)
        entities = triage_service.extract_entities(text_content)
        
        print(f"   [OUT] Intent: {intent} | Entities: {entities}")
        
        # 4. Update Session
        # Use sender (remoteJid) as phone identifier for now.
        phone = sender.split("@")[0]
        
        session_result = session_manager.update_session(
            phone=phone,
            message=text_content,
            intent=intent,
            entities=entities
        )
        print(f"   [SESSION] State: {session_result['status']}")
        
        # 5. Auto-Reply
        reply_msg = session_result.get("reply_message")
        if reply_msg:
            replier_service.send_text(sender, reply_msg)
    
    return {
        "status": "processed",
        "input": text_content,
        "intent": intent,
        "session": "updated"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "ffmpeg": "unknown (check logs)"}
