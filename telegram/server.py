from fastapi import FastAPI, Header, HTTPException, Depends
from webhooks import update_chat_history, receive_audio_response
from pydantic import BaseModel
from uuid import UUID
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

async def get_api_key(api_key: str = Header(None)):
    if api_key != os.getenv("API-HEADER"):
        raise HTTPException(status_code=400, detail="Invalid API Key")
    return api_key

class ChatUpdate(BaseModel):
    user_chat_id: str
    message_id: str
    bot_message_text: str



@app.put("/update-chat-history")
async def update_chat_endpoint(chat_update: ChatUpdate, api_key: str = Depends(get_api_key)):
    result = update_chat_history(chat_update.message_id, chat_update.bot_message_text)
    return result

class AudioUpdate(BaseModel):
    user_chat_id: str
    message_id: str
    audio_file: str



@app.post("/receieve-audio-response")
async def receive_audio_endpoint(audio_update: AudioUpdate, api_key: str = Depends(get_api_key)):
    result = await receive_audio_response(audio_update.user_chat_id, audio_update.audio_file)
    return result

