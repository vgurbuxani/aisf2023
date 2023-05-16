import logging
from telegram import Update, Invoice, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, SuccessfulPayment
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, PreCheckoutQueryHandler

import os
import locale
import uuid
from dotenv import load_dotenv
from supabase import create_client
from connector import send_recent_chats

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
locale.setlocale( locale.LC_ALL, '' )

#TODO @ilaffey2 only one of these at a time. maybe a semaphore?
async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Add to DB
    message_uuid = str(uuid.uuid4())
    user_message_text = update.message.text
    user_chat_id = update.effective_chat.id
    supabase.table("chats").insert({"message_id": message_uuid, 
                                    "user_chat_id": user_chat_id, 
                                    "user_message_text": user_message_text,
                                    "bot_message_loading":  True}).execute()
    print("MESSAGE ADDED WITH")
    print(f"message_id: {message_uuid}")
    print(f"user_chat_id: {user_chat_id}")
    print(f"user_message_text: {user_message_text}")

    #Send most recent messages to backend
    send_recent_chats(user_chat_id, message_uuid)

    await update.message.reply_text("Loading")




if __name__ == '__main__':
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    

    chat_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat)
    application.add_handler(chat_handler)



    
    application.run_polling()