import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import psycopg2

# Initialize logging
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = '7766655798:AAHacsx-GCkJDBI6FYAiNpNH96IFPTaDHkg'
DATABASE_URL = 'postgres://default:gaFjrs9b4oLK@ep-ancient-smoke-a1pliqaw.ap-southeast-1.aws.neon.tech:5432/verceldb?sslmode=require'
ADMIN_CHAT_ID = 6826870863

# Database connection
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Sign In", callback_data='signin')],
        [InlineKeyboardButton("Sign Up", callback_data='signup')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Welcome! Please choose an option:', reply_markup=reply_markup)

def handle_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    if query.data == 'signup':
        context.user_data['status'] = 'signup'
        query.message.reply_text('Please enter your WhatsApp number:')
    elif query.data == 'signin':
        check_login(update, context)

def handle_message(update: Update, context: CallbackContext) -> None:
    if 'status' in context.user_data and context.user_data['status'] == 'signup':
        if 'whatsapp_number' not in context.user_data:
            context.user_data['whatsapp_number'] = update.message.text
            update.message.reply_text('Please enter your Telegram username:')
        else:
            context.user_data['telegram_username'] = update.message.text
            keyboard = [[InlineKeyboardButton("Confirm", callback_data='confirm_signup')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(f"Confirm your details:\nWhatsApp Number: {context.user_data['whatsapp_number']}\nTelegram Username: {context.user_data['telegram_username']}", reply_markup=reply_markup)

def confirm_signup(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    
    chat_id = query.message.chat_id
    whatsapp_number = context.user_data['whatsapp_number']
    telegram_username = context.user_data['telegram_username']
    
    with conn.cursor() as cur:
        cur.execute("INSERT INTO users (chat_id, whatsapp_number, telegram_username) VALUES (%s, %s, %s) ON CONFLICT (chat_id) DO NOTHING", (chat_id, whatsapp_number, telegram_username))
        conn.commit()

    context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"New User Joined: WhatsApp Number: {whatsapp_number}, Telegram Username: {telegram_username}")
    query.message.reply_text('You have successfully signed up!')

def check_login(update: Update, context: CallbackContext) -> None:
    chat_id = update.callback_query.message.chat_id
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE chat_id=%s", (chat_id,))
        user = cur.fetchone()
    if user:
        update.callback_query.message.reply_text('Successfully Logged In')
    else:
        update.callback_query.message.reply_text('Please Sign Up')

def admin_broadcast(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id == ADMIN_CHAT_ID:
        command = update.message.text.split(' ', 1)
        if len(command) == 2:
            message = command[1]
            if command[0] == '/user-text':
                user_id = int(message.split(' ')[0])
                text = ' '.join(message.split(' ')[1:])
                context.bot.send_message(chat_id=user_id, text=text)
            elif command[0] == '/all-text':
                with conn.cursor() as cur:
                    cur.execute("SELECT chat_id FROM users")
                    user_ids = cur.fetchall()
                for user_id in user_ids:
                    context.bot.send_message(chat_id=user_id[0], text=message)

def main() -> None:
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(handle_callback))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CommandHandler('user-text', admin_broadcast))
    dispatcher.add_handler(CommandHandler('all-text', admin_broadcast))

    updater.start_webhook(listen='0.0.0.0', port=int(PORT), url_path=BOT_TOKEN)
    updater.bot.setWebhook(RENDER_URL + BOT_TOKEN)

    updater.idle()

if __name__ == '__main__':
    main()
