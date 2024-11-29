from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# A dictionary to store user data
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data.setdefault(chat_id, {})
    
    keyboard = [
        [InlineKeyboardButton("Sign In", callback_data='signin')],
        [InlineKeyboardButton("Sign Up", callback_data='signup')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Welcome! Please choose an option:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id

    if query.data == "signin":
        if chat_id in user_data and "details" in user_data[chat_id]:
            await query.edit_message_text("Successfully Logged In.")
        else:
            await query.edit_message_text("Please Sign Up first.")
    
    elif query.data == "signup":
        user_data[chat_id]['step'] = 'awaiting_details'
        await query.edit_message_text("Please enter your WhatsApp number and Telegram username in this format:\n\n`<WhatsApp Number>, <Telegram Username>`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if chat_id in user_data and user_data[chat_id].get('step') == 'awaiting_details':
        try:
            whatsapp_number, telegram_username = map(str.strip, text.split(','))
            user_data[chat_id]['details'] = {
                "WhatsApp": whatsapp_number,
                "Telegram": telegram_username
            }
            user_data[chat_id]['step'] = 'confirm'
            keyboard = [[InlineKeyboardButton("Confirm", callback_data='confirm')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Please confirm your details:\n\nWhatsApp: {whatsapp_number}\nTelegram: {telegram_username}",
                reply_markup=reply_markup
            )
        except ValueError:
            await update.message.reply_text("Invalid format! Please use:\n\n`<WhatsApp Number>, <Telegram Username>`", parse_mode="Markdown")
    else:
        await update.message.reply_text("Please use the /start command.")

async def confirm_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id

    if chat_id in user_data and user_data[chat_id].get('step') == 'confirm':
        user_data[chat_id]['step'] = None  # Clear the step
        await query.edit_message_text("Your details have been saved successfully.")
    else:
        await query.edit_message_text("No details to confirm. Please start with Sign Up.")

def main():
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(CallbackQueryHandler(confirm_details, pattern="^confirm$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
