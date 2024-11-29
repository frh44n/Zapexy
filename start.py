from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = "https://ecfmwdaeekmhsjscrnol.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVjZm13ZGFlZWttaHNqc2Nybm9sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI5MTA1NzMsImV4cCI6MjA0ODQ4NjU3M30.PbJKaSTLwfCXGxaph5HofBlFyCU1zQ8uhYEYHIDkg58"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
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
        # Check if chat ID exists in the database
        response = supabase.table("users").select("id").eq("id", chat_id).execute()
        if response.data:
            await query.edit_message_text("Successfully Logged In.")
        else:
            await query.edit_message_text("Please Sign Up first.")
    
    elif query.data == "signup":
        context.user_data["step"] = "awaiting_details"
        await query.edit_message_text(
            "Please enter your WhatsApp number and Telegram username in this format:\n\n"
            "`<WhatsApp Number>, <Telegram Username>`", 
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await update.message.reply_text(
                f"Please confirm your details:\n\nWhatsApp: {whatsapp_number}\nTelegram: {telegram_username}",
                reply_markup=reply_markup
            )
        except ValueError:
            await update.message.reply_text(
                "Invalid format! Please use:\n\n`<WhatsApp Number>, <Telegram Username>`", 
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text("Please use the /start command.")

async def confirm_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id

    if context.user_data.get("step") == "confirm":
        details = context.user_data.pop("details", {})
        # Save details to Supabase
        response = supabase.table("users").upsert(details).execute()
        if response.status_code == 201:
            await query.edit_message_text("Your details have been saved successfully.")
        else:
            await query.edit_message_text("Failed to save your details. Please try again.")
    else:
        await query.edit_message_text("No details to confirm. Please start with Sign Up.")

def main():
    app = ApplicationBuilder().token("7766655798:AAHacsx-GCkJDBI6FYAiNpNH96IFPTaDHkg").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(confirm_details, pattern="^confirm$"))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
