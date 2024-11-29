import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import filters
from flask import Flask, request
import os

# Setting up logging for the bot
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)

# GitHub user.txt file location
USER_FILE_PATH = "https://github.com/frh44n/Zapexy/blob/main/user.txt"

# Helper functions to read and write user data
def read_user_data():
    try:
        # Read the user data file from GitHub (or you can use another file storage method)
        import requests
        response = requests.get(USER_FILE_PATH)
        return response.text.splitlines()
    except Exception as e:
        logger.error(f"Error reading user data: {e}")
        return []

def save_user_data(chat_id, data):
    try:
        # Save user data to GitHub or a text file
        with open('user.txt', 'a') as file:
            file.write(f"{chat_id},{data['whatsapp']},{data['telegram_username']}\n")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

# Command handlers
def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    keyboard = [
        [InlineKeyboardButton("Signin", callback_data="signin")],
        [InlineKeyboardButton("Signup", callback_data="signup")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Welcome! Choose an option:', reply_markup=reply_markup)

def signup(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Back", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.answer()
    update.callback_query.edit_message_text('Please enter your WhatsApp number and Telegram username (separate by comma):', reply_markup=reply_markup)
    return 'awaiting_signup'

def handle_signup_input(update: Update, context: CallbackContext):
    user_input = update.message.text
    if "," in user_input:
        whatsapp, telegram_username = user_input.split(",", 1)
        context.user_data['whatsapp'] = whatsapp.strip()
        context.user_data['telegram_username'] = telegram_username.strip()

        keyboard = [
            [InlineKeyboardButton("Confirm", callback_data="confirm_signup")],
            [InlineKeyboardButton("Back", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Confirm your information:', reply_markup=reply_markup)
    else:
        update.message.reply_text('Invalid input. Please enter your WhatsApp number and Telegram username, separated by a comma.')

def confirm_signup(update: Update, context: CallbackContext):
    chat_id = update.callback_query.message.chat_id
    data = context.user_data
    save_user_data(chat_id, data)
    update.callback_query.answer()
    update.callback_query.edit_message_text("Signup successful. You can now login.")

def signin(update: Update, context: CallbackContext):
    chat_id = update.callback_query.message.chat_id
    users = read_user_data()
    user_found = any(str(chat_id) in line for line in users)
    if user_found:
        update.callback_query.answer()
        update.callback_query.edit_message_text("Successfully Logged In.")
    else:
        update.callback_query.answer()
        update.callback_query.edit_message_text("Please Sign Up.")

# Handlers for the different states
def handle_message(update: Update, context: CallbackContext):
    if 'awaiting_signup' in context.user_data:
        handle_signup_input(update, context)

# Webhook setup
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json_str, bot)
    dispatcher.process_update(update)
    return 'OK'

# Main function to set up the bot and Flask server
def main():
    token = '7766655798:AAHacsx-GCkJDBI6FYAiNpNH96IFPTaDHkg'  # Replace with your bot token
    updater = Updater(token, use_context=True)
    global bot
    bot = updater.bot
    dispatcher = updater.dispatcher

    # Command and callback handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(signup, pattern="signup"))
    dispatcher.add_handler(CallbackQueryHandler(signin, pattern="signin"))
    dispatcher.add_handler(CallbackQueryHandler(confirm_signup, pattern="confirm_signup"))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Set webhook to your Render app
    app_url = 'https://zapexypythom.onrender.com/7766655798:AAHacsx-GCkJDBI6FYAiNpNH96IFPTaDHkg'  # Replace with your Render webhook URL
    bot.set_webhook(url=app_url)

    # Start the Flask server
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
