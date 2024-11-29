import os
import psycopg2
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import logging
import asyncio
from flask import Flask, request
import requests

# Load environment variables from .env file
load_dotenv()

# Telegram API Key from .env
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Connection
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

# Webhook function
async def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_API_KEY}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    if response.status_code == 200:
        print("Webhook set successfully.")
    else:
        print(f"Error setting webhook: {response.text}")

# Handle '/start' command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()

    if result:
        buttons = [
            [InlineKeyboardButton("Login", callback_data='login')],
            [InlineKeyboardButton("SignUp", callback_data='signup')]
        ]
    else:
        buttons = [
            [InlineKeyboardButton("SignUp", callback_data='signup')]
        ]

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Welcome! Please choose an option:", reply_markup=reply_markup)

# Handle SignUp button
async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    await update.message.reply_text("Please enter your WhatsApp number and Telegram username in the format:\n`<WhatsApp number> <Telegram username>`")

# Handle received user info during SignUp
async def handle_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    user_info = update.message.text.split()

    if len(user_info) == 2:
        whatsapp_number, telegram_username = user_info
        await update.message.reply_text(f"Your WhatsApp number: {whatsapp_number}\nYour Telegram username: {telegram_username}\nPlease confirm.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data='confirm')]
        ]))
        context.user_data['whatsapp'] = whatsapp_number
        context.user_data['username'] = telegram_username
    else:
        await update.message.reply_text("Invalid input. Please enter in the format: <WhatsApp number> <Telegram username>")

# Handle Confirm button (Save user data)
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    whatsapp = context.user_data.get('whatsapp')
    username = context.user_data.get('username')

    if whatsapp and username:
        cursor.execute("INSERT INTO users (chat_id, whatsapp, username) VALUES (%s, %s, %s)", (chat_id, whatsapp, username))
        conn.commit()
        await update.message.reply_text("SignUp successful! You can now log in.")
    else:
        await update.message.reply_text("Something went wrong. Please try again.")

# Handle Login button
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()

    if result:
        await update.message.reply_text("Successfully Logged In!")
    else:
        await update.message.reply_text("Please Sign Up first.")

# Setup Application and Handlers
async def main():
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    # Handlers for different commands and actions
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(signup, pattern='signup'))
    application.add_handler(CallbackQueryHandler(confirm, pattern='confirm'))
    application.add_handler(CallbackQueryHandler(login, pattern='login'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_info))

    # Set the webhook
    bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

if __name__ == '__main__':
    main()
    app.run(host='0.0.0.0', port=5000)
