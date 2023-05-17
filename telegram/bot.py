import logging
import uuid
from telegram import Update, Invoice, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, SuccessfulPayment
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, PreCheckoutQueryHandler

import os
import locale
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

async def invoice(update: Update, context: ContextTypes.DEFAULT_TYPE, credits: int):
    await context.bot.send_invoice(chat_id=update.effective_chat.id, title="Credit Purchase", 
                                   description="Purchase credits for influencer.ai", 
                                   payload="test", provider_token=os.getenv("PAYMENT_BOT_TOKEN"), currency="USD",
                                   prices=[LabeledPrice("Credits:", credits)] )
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Securely pay with Stripe. Select a deposit amount:", 
                    reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="$5",callback_data="500" ), InlineKeyboardButton(text="$10", callback_data="1000")],
                     [InlineKeyboardButton(text="$25",callback_data="2500" ), InlineKeyboardButton(text="$50", callback_data="5000")],
                     [InlineKeyboardButton(text="$100",callback_data="10000" ), InlineKeyboardButton(text="$250", callback_data="25000")],
                     [InlineKeyboardButton(text="$500",callback_data="50000" )
                     ]]))

# This will be called when an inline button is pressed.
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query_data = query.data

    try:
        credits_to_buy = int(query_data, base=10)
        await invoice(update, context,credits_to_buy)
    except Exception as e:
        print(e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error creating Stripe Payment Link.")
        
async def insert_or_update_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, credits: int):
    try:
        supabase.table("customers").insert({"id": update.effective_chat.id, "balance" : credits}).execute()
    except Exception as e1:
        # print(e)
        try:
            prev_balance = supabase.table("customers").select("balance").eq("id", update.effective_chat.id).execute().data[0]["balance"]
            supabase.table("customers").update({"balance" : prev_balance + credits}).eq("id", update.effective_chat.id).execute()
        except Exception as e2:
            print("mayday")
            print(e1)
            print(e2)

            await context.bot.send_message(chat_id=update.effective_chat.id, text="Error processing payments, please contact: %SOMEBODY%.")



async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        balance = supabase.table("customers").select("balance").eq("id", update.effective_chat.id).execute().data[0]["balance"]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Your balance is {locale.currency(balance/100,grouping=True)}")
    except Exception as e:
        print (e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Your balance is $0")


async def has_funds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        balance = supabase.table("customers").select("balance").eq("id", update.effective_chat.id).execute().data[0]["balance"]
        return balance > 10
    except:
        return False


# This will be called when a pre-checkout query is created
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Here you can check the info in the pre_checkout_query and decide whether to confirm the order or not
    # For the sake of the example, let's just confirm all orders
    pre_checkout_query = update.pre_checkout_query
    print(pre_checkout_query)
    await context.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# This will be called when a successful payment is made
async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    successful_payment: SuccessfulPayment = update.message.successful_payment
    # Here you can proceed with delivering the goods or services purchased by the user
    # For the sake of the example, let's just send a thank you message

    # TODO @ilaffey2 Dump payments somewhere to live forever
    print(successful_payment)
    await insert_or_update_balance(update, context, successful_payment.total_amount)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Thank you for your purchase!")
    await balance(update, context)


#TODO @ilaffey2 only one of these at a time. maybe a semaphore?
async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await has_funds(update, context):
        await update.message.reply_text("Insufficient balance. Add more funds with /deposit to get started!")
        return

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("You have started %CREATOR% BOT experience")


if __name__ == '__main__':
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    

    deposit_handler = CommandHandler('deposit', deposit)
    application.add_handler(deposit_handler)


    balance_handler = CommandHandler('balance', balance)
    application.add_handler(balance_handler)

    button_handler = CallbackQueryHandler(button_callback)
    application.add_handler(button_handler)

    chat_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat)
    application.add_handler(chat_handler)

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)


    # Create handlers
    pre_checkout_handler = PreCheckoutQueryHandler(precheckout_callback)
    application.add_handler(pre_checkout_handler)

    successful_payment_handler = MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    application.add_handler(successful_payment_handler)

    
    application.run_polling()