from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = "https://ecfmwdaeekmhsjscrnol.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVjZm13ZGFlZWttaHNqc2Nybm9sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI5MTA1NzMsImV4cCI6MjA0ODQ4NjU3M30.PbJKaSTLwfCXGxaph5HofBlFyCU1zQ8uhYEYHIDkg58"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Telegram bot handlers
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("Sign In", callback_data='signin')],
        [InlineKeyboardButton("Sign Up", callback_data='signup')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome! Please choose an option:", reply_markup=reply_markup)

def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id

    if query.data == "signin":
        # Check if chat ID exists in the database
        response = supabase.table("users").select("id").eq("id", chat_id).execute()
        if response.data:
            query.edit_message_text("Successfully Logged In.")
        else:
            query.edit_message_text("Please Sign Up first.")
    
    elif query.data == "signup":
        context.user_data["step"] = "awaiting_details"
        query.edit_message_text(
            "Please enter your WhatsApp number and Telegram username in this format:\n\n"
            "`<WhatsApp Number>, <Telegram Username>`", 
            parse_mode="Markdown"
        )

def handle_message(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text

    if context.user_data.get("step") == "awaiting_details":
        try:
            whatsapp_number, telegram_username = map(str.strip, text.split(','))
            context.user_data["details"] = {
                "id": chat_id,
                "whatsapp": whatsapp_number,
                "telegram": telegram_username
            }
            context.user_data["step"] = "confirm"
            keyboard = [[InlineKeyboardButton("Confirm", callback_data='confirm')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                f"Please confirm your details:\n\nWhatsApp: {whatsapp_number}\nTelegram: {telegram_username}",
                reply_markup=reply_markup
            )
        except ValueError:
            update.message.reply_text(
                "Invalid format! Please use:\n\n`<WhatsApp Number>, <Telegram Username>`", 
                parse_mode="Markdown"
            )
    else:
        update.message.reply_text("Please use the /start command.")

def confirm_details(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id

    if context.user_data.get("step") == "confirm":
        details = context.user_data.pop("details", {})
        # Save details to Supabase
        response = supabase.table("users").upsert(details).execute()
        if response.status_code == 201:
            query.edit_message_text("Your details have been saved successfully.")
        else:
            query.edit_message_text("Failed to save your details. Please try again.")
    else:
        query.edit_message_text("No details to confirm. Please start with Sign Up.")

def main():
    updater = Updater("7766655798:AAHacsx-GCkJDBI6FYAiNpNH96IFPTaDHkg", use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(handle_button))
    dispatcher.add_handler(CallbackQueryHandler(confirm_details, pattern="^confirm$"))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    print("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
