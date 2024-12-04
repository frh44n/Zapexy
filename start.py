import logging
import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# Define a few command handlers. These usually take the two arguments update and context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Sign In", callback_data='signin'),
         InlineKeyboardButton("Sign Up", callback_data='signup')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please choose:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'signin':
        # SignIn logic here
        chat_id = query.message.chat_id
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE chat_id = %s", (chat_id,))
        result = cursor.fetchone()
        if result:
            await query.edit_message_text(text="Successfully Logged In")
        else:
            await query.edit_message_text(text="Please Sign Up.")
        cursor.close()

    elif query.data == 'signup':
        # SignUp logic here
        await query.edit_message_text(text="Please enter your WhatsApp Number, Telegram Username, and PhonePe Number in the format: /signup <whatsapp> <username> <phonepe>")

async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        whatsapp_number, telegram_username, phonepe_number = context.args
        chat_id = update.message.chat_id

        keyboard = [[InlineKeyboardButton("Confirm", callback_data='confirm')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['user_info'] = (chat_id, whatsapp_number, telegram_username, phonepe_number)
        await update.message.reply_text(f"Confirm your details:\nWhatsApp: {whatsapp_number}\nTelegram Username: {telegram_username}\nPhonePe: {phonepe_number}", reply_markup=reply_markup)
    except ValueError:
        await update.message.reply_text('Please enter the details in the correct format: /signup <whatsapp> <username> <phonepe>')

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id, whatsapp_number, telegram_username, phonepe_number = context.user_data['user_info']
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (chat_id, whatsapp_number, telegram_username, phonepe_number) VALUES (%s, %s, %s, %s)",
                   (chat_id, whatsapp_number, telegram_username, phonepe_number))
    conn.commit()
    cursor.close()
    await query.edit_message_text(text="You have successfully signed up!")

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for new_member in update.message.new_chat_members:
        chat_id = update.message.chat_id
        whatsapp_number, telegram_username, phonepe_number = context.user_data.get(new_member.id, ("Unknown", "Unknown", "Unknown"))
        admin_chat_id = 6826870863  # Admin chat ID
        await context.bot.send_message(chat_id=admin_chat_id, text=f"New User Joined\nUser ID: {new_member.id}\nWhatsApp Number: {whatsapp_number}")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = ' '.join(context.args)
    chat_id = update.message.chat_id
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users")
    results = cursor.fetchall()
    for user in results:
        await context.bot.send_message(chat_id=user[0], text=message)
    cursor.close()

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        chat_id, amount = context.args
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET deposit_balance = deposit_balance + %s WHERE chat_id = %s", (amount, chat_id))
        conn.commit()
        cursor.close()
        await context.bot.send_message(chat_id=chat_id, text="Your Deposit Balance has been updated.")
    except ValueError:
        await update.message.reply_text('Please enter the command in the correct format: /add <chat_id> <amount>')

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    cursor = conn.cursor()
    cursor.execute("SELECT earning_balance FROM users WHERE chat_id = %s", (chat_id,))
    result = cursor.fetchone()
    if result and result[0] >= 5:
        await update.message.reply_text('How much would you like to withdraw?')
        context.user_data['withdraw'] = True
    else:
        await update.message.reply_text('Minimum amount required to withdraw is 5')
    cursor.close()

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('withdraw'):
        amount = float(update.message.text)
        chat_id = update.message.chat_id
        cursor = conn.cursor()
        cursor.execute("SELECT earning_balance, phonepe_number FROM users WHERE chat_id = %s", (chat_id,))
        result = cursor.fetchone()
        if result and result[0] >= amount:
            await context.bot.send_message(chat_id=6826870863, text=f"Withdrawal Request\nUser ID: {chat_id}\nEarning Balance: {result[0]}\nWithdrawal Request: {amount}\nPhonePe Number: {result[1]}")
            cursor.execute("UPDATE users SET earning_balance = earning_balance - %s WHERE chat_id = %s", (amount, chat_id))
            conn.commit()
            await update.message.reply_text("Your withdrawal request has been submitted.")
        else:
            await update.message.reply_text('Insufficient balance.')
        cursor.close()
        context.user_data['withdraw'] = False

async def main() -> None:
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.environ['BOT_TOKEN']).build()

    # Get the dispatcher to register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("signup", signup))
    application.add_handler(CallbackQueryHandler(confirm))
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("add", add_balance))
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'\d+'), handle_withdraw_amount))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))

    # Start the Bot
    updater.start_webhook(listen='0.0.0.0',
                          port=int(os.environ.get('PORT', '8443')),
                          url_path=os.environ['BOT_TOKEN'])
    updater.bot.setWebhook(f"{os.environ['RENDER_URL']}/{os.environ['BOT_TOKEN']}")

    updater.idle()

if __name__ == '__main__':
    asyncio.run(main())
