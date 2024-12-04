import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import psycopg2
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = '7766655798:AAHacsx-GCkJDBI6FYAiNpNH96IFPTaDHkg'
DATABASE_URL = os.getenv('POSTGRES_URL')
PORT = int(os.environ.get('PORT', '8443'))
RENDER_URL = 'https://zapexypythom.onrender.com/'
ADMIN_CHAT_ID = '6826870863'  # Replace with your admin chat ID

# Database connection
try:
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    logging.info("Database connection established.")
except Exception as e:
    logging.error(f"Error connecting to the database: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE chat_id=%s", (chat_id,))
            user = cur.fetchone()
        
        if user:
            await update.message.reply_text('Welcome back! You are already registered.')
        else:
            await update.message.reply_text("You're most welcome. Click /signup for Account Registration.")
            context.user_data['status'] = 'signup_prompt'
    except Exception as e:
        logging.error(f"Error during start command: {e}")

async def signup_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Sign In", callback_data='signin')],
        [InlineKeyboardButton("Sign Up", callback_data='signup')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose an option:', reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    logging.info(f"Callback query data: {query.data}")
    logging.info(f"Context user data before handling callback: {context.user_data}")
    
    if query.data == 'signup':
        context.user_data['status'] = 'signup'
        await query.message.reply_text('Please enter your WhatsApp number:')
    elif query.data == 'signin':
        await check_login(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info(f"Received message: {update.message.text}")
    logging.info(f"Context user data: {context.user_data}")

    if 'status' in context.user_data and context.user_data['status'] == 'signup':
        if 'whatsapp_number' not in context.user_data:
            context.user_data['whatsapp_number'] = update.message.text
            await update.message.reply_text('Please enter your Telegram username:')
        else:
            context.user_data['telegram_username'] = update.message.text
            keyboard = [[InlineKeyboardButton("Confirm", callback_data='confirm_signup')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"Confirm your details:\nWhatsApp Number: {context.user_data['whatsapp_number']}\nTelegram Username: {context.user_data['telegram_username']}", reply_markup=reply_markup)

async def confirm_signup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    whatsapp_number = context.user_data.get('whatsapp_number', 'N/A')
    telegram_username = context.user_data.get('telegram_username', 'N/A')

    logging.info(f"Confirming signup for chat_id: {chat_id}, WhatsApp Number: {whatsapp_number}, Telegram Username: {telegram_username}")
    
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (chat_id, whatsapp_number, telegram_username) VALUES (%s, %s, %s) ON CONFLICT (chat_id) DO NOTHING",
                (chat_id, whatsapp_number, telegram_username)
            )
            conn.commit()
        
        logging.info("User information inserted successfully.")
        await query.message.reply_text('You have successfully signed up!')
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"New User Joined: WhatsApp Number: {whatsapp_number}, Telegram Username: {telegram_username}")
    except Exception as e:
        logging.error(f"Error during confirm_signup: {e}")
        await query.message.reply_text('There was an error during sign up. Please try again.')

async def check_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.callback_query.message.chat_id
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE chat_id=%s", (chat_id,))
            user = cur.fetchone()
        
        if user:
            await update.callback_query.message.reply_text('Successfully Logged In')
        else:
            await update.callback_query.message.reply_text('Please Sign Up')
    except Exception as e:
        logging.error(f"Error during check_login: {e}")
        await update.callback_query.message.reply_text('There was an error during login. Please try again.')

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id == int(ADMIN_CHAT_ID):
        command = update.message.text.split(' ', 1)
        if len(command) == 2:
            message = command[1]
            if command[0] == '/usertext':
                user_id = int(message.split(' ')[0])
                text = ' '.join(message.split(' ')[1:])
                await context.bot.send_message(chat_id=user_id, text=text)
            elif command[0] == '/alltext':
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT chat_id FROM users")
                        user_ids = cur.fetchall()
                    for user_id in user_ids:
                        await context.bot.send_message(chat_id=user_id[0], text=message)
                except Exception as e:
                    logging.error(f"Error during admin_broadcast: {e}")

async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id == int(ADMIN_CHAT_ID):
        command = update.message.text.split(' ', 1)
        if len(command) == 2:
            user_id = int(command[1])
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users WHERE chat_id = %s", (user_id,))
                    conn.commit()
                await update.message.reply_text(f"User with chat_id {user_id} has been deleted.")
            except Exception as e:
                logging.error(f"Error during delete_user: {e}")
                await update.message.reply_text('There was an error deleting the user. Please try again.')
        else:
            await update.message.reply_text("Please provide the chat_id of the user you want to delete. Usage: /deleteuser <chat_id>")

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signup", signup_prompt))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler('usertext', admin_broadcast))
    application.add_handler(CommandHandler('alltext', admin_broadcast))
    application.add_handler(CommandHandler('deleteuser', delete_user))

    application.run_webhook(listen='0.0.0.0', port=PORT, url_path=BOT_TOKEN, webhook_url=RENDER_URL + BOT_TOKEN)

if __name__ == '__main__':
    main()
