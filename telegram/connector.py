import os
import json
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

def send_recent_chats(user_chat_id: str, most_recent_message_id: str):
    result = supabase.table("chats").select("*").order("created_at", desc=True).limit(10).execute()

    chats = []
    for row in result.data:
        chats.append(f'USER MESSAGE: {row["user_message_text"]}')

        if row["bot_message_loading"]:
            break

        chats.append(f'BOT MESSAGE: {row["bot_message_text"]}')
    chats_json = json.dumps({"user_chat_id": user_chat_id, "message_id": most_recent_message_id, "chats": chats})

    backend_url = os.getenv("BACKEND_URL") + "/receiver"

    # Send a POST request to the backend
    response = requests.post(backend_url, data=chats_json, headers={'Content-Type': 'application/json'})

    # Check the response
    if response.status_code == 200:
        print("Chats sent successfully!")
    else:
        print(f"Error sending chats: {response.status_code}, {response.text}")

