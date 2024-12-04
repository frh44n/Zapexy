import logging
import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# Define a few command handlers. These usually take the two arguments update and context.
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Sign In", callback_data='signin'),
         InlineKeyboardButton("Sign Up", callback_data='signup')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'signin':
        # SignIn logic here
        chat_id = query.message.chat_id
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
        result = cursor.fetchone()
        if result:
            query.edit_message_text(text="Successfully Logged In")
        else:
            query.edit_message_text(text="Please Sign Up.")
        cursor.close()

    elif query.data == 'signup':
        # SignUp logic here
        query.edit_message_text(text="Please enter your WhatsApp Number, Telegram Username, and PhonePe Number in the format: /signup <whatsapp> <username> <phonepe>")

def signup(update: Update, context: CallbackContext) -> None:
    try:
        whatsapp_number, telegram_username, phonepe_number = context.args
        chat_id = update.message.chat_id

        keyboard = [[InlineKeyboardButton("Confirm", callback_data='confirm')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['user_info'] = (chat_id, whatsapp_number, telegram_username, phonepe_number)
        update.message.reply_text(f"Confirm your details:\nWhatsApp: {whatsapp_number}\nTelegram Username: {telegram_username}\nPhonePe: {phonepe_number}", reply_markup=reply_markup)
    except ValueError:
        update.message.reply_text('Please enter the details in the correct format: /signup <whatsapp> <username> <phonepe>')

def confirm(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    chat_id, whatsapp_number, telegram_username, phonepe_number = context.user_data['user_info']
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (chat_id, whatsapp_number, telegram_username, phonepe_number) VALUES (%s, %s, %s, %s)",
                   (chat_id, whatsapp_number, telegram_username, phonepe_number))
    conn.commit()
    cursor.close()
    query.edit_message_text(text="You have successfully signed up!")

def handle_new_member(update: Update, context: CallbackContext) -> None:
    for new_member in update.message.new_chat_members:
        chat_id = update.message.chat_id
        whatsapp_number, telegram_username, phonepe_number = context.user_data.get(new_member.id, ("Unknown", "Unknown", "Unknown"))
        admin_chat_id = 6826870863  # Admin chat ID
        context.bot.send_message(chat_id=admin_chat_id, text=f"New User Joined\nUser ID: {new_member.id}\nWhatsApp Number: {whatsapp_number}")

def broadcast_message(update: Update, context: CallbackContext) -> None:
    message = ' '.join(context.args)
    chat_id = update.message.chat_id
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users")
    results = cursor.fetchall()
    for user in results:
        context.bot.send_message(chat_id=user[0], text=message)
    cursor.close()

def add_balance(update: Update, context: CallbackContext) -> None:
    try:
        chat_id, amount = context.args
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET deposit_balance = deposit_balance + %s WHERE chat_id = %s", (amount, chat_id))
        conn.commit()
        cursor.close()
        context.bot.send_message(chat_id=chat_id, text="Your Deposit Balance has been updated.")
    except ValueError:
        update.message.reply_text('Please enter the command in the correct format: /add <chat_id> <amount>')

def withdraw(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    cursor = conn.cursor()
    cursor.execute("SELECT earning_balance FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()
    if result and result[0] >= 5:
        update.message.reply_text('How much would you like to withdraw?')
        context.user_data['withdraw'] = True
    else:
        update.message.reply_text('Minimum amount required to withdraw is 5')
    cursor.close()

def handle_withdraw_amount(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('withdraw'):
        amount = float(update.message.text)
        chat_id = update.message.chat_id
        cursor = conn.cursor()
        cursor.execute("SELECT earning_balance, phonepe_number FROM users WHERE chat_id = %s", (chat_id,))
        result = cursor.fetchone()
        if result and result[0] >= amount:
            context.bot.send_message(chat_id=6826870863, text=f"Withdrawal Request\nUser ID: {chat_id}\nEarning Balance: {result[0]}\nWithdrawal Request: {amount}\nPhonePe Number: {result[1]}")
            cursor.execute("UPDATE users SET earning_balance = earning_balance - %s WHERE chat_id = %s", (amount, chat_id))
            conn.commit()
            update.message.reply_text("Your withdrawal request has been submitted.")
        else:
            update.message.reply_text('Insufficient balance.')
        cursor.close()
        context.user_data['withdraw'] = False

def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(os.environ['BOT_TOKEN'])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(CommandHandler("signup", signup))
    dispatcher.add_handler(CallbackQueryHandler(confirm))
    dispatcher.add_handler(CommandHandler("broadcast", broadcast_message))
    dispatcher.add_handler(CommandHandler("add", add_balance))
    dispatcher.add_handler(CommandHandler("withdraw", withdraw))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.regex(r'\d+'), handle_withdraw_amount))
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, handle_new_member))

    # Start the Bot
    updater.start_webhook(listen='0.0.0.0',
                          port=int(os.environ.get('PORT', '8443')),
                          url_path=os.environ['BOT_TOKEN'])
    updater.bot.setWebhook(f"{os.environ['RENDER_URL']}/{os.environ['BOT_TOKEN']}")

    updater.idle()

if __name__ == '__main__':
    main()
