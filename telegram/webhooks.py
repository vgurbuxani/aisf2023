from supabase import create_client, Client
from uuid import UUID
import os
from dotenv import load_dotenv
from telegram import Bot 
import aiohttp
import asyncio
from pydub import AudioSegment
from io import BytesIO



load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
bot = Bot(os.getenv("TELEGRAM_BOT_TOKEN"))

def update_chat_history(message_id: UUID, bot_message_text: str):
    try:
        response = supabase.table("chats").update({"bot_message_text": bot_message_text, "bot_message_loading": False}).eq("message_id", message_id).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        print (e)
        return {"status": "error", "message": str(e)}

async def download_file(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()

async def convert_audio(audio_bytes):
    audio = AudioSegment.from_mp3(BytesIO(audio_bytes))
    # Convert audio to opus
    audio.export("temp.ogg", format="ogg", codec="libopus")
    with open("temp.ogg", 'rb') as f:
        return f.read()

async def receive_audio_response(user_chat_id: str, audio_file_url: str):
    # Download the audio file
    audio_bytes = await download_file(audio_file_url)

    # Convert the audio to OGG format
    converted_audio_bytes = await convert_audio(audio_bytes)

    # Send the converted audio
    async with bot:
        await bot.send_voice(chat_id=user_chat_id, voice=BytesIO(converted_audio_bytes))
    
    return {"status": "success"}