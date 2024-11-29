import os
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Set up database connection using environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Start command: check if user is in the database
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Check if user is already in the database
    cur.execute("SELECT * FROM users WHERE chat_id = %s", (user_id,))
    user = cur.fetchone()

    if user:
        # If user exists, show SignIn and SignUp buttons
        buttons = [
            [InlineKeyboardButton("Sign In", callback_data="signin")],
            [InlineKeyboardButton("Sign Up", callback_data="signup")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("Welcome back! Choose an option:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("You are not registered yet. Please Sign Up.")

# Handle SignUp button press: ask for WhatsApp number
async def signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Ask for WhatsApp number
    await update.message.reply_text("Please enter your WhatsApp number:")

# Handle WhatsApp number input
async def handle_signup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    context.user_data["whatsapp"] = user_input
    # Ask for Telegram username
    await update.message.reply_text("Please enter your Telegram username:")

# Handle Telegram username input and save to database
async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    whatsapp = context.user_data["whatsapp"]
    
    user_id = update.effective_user.id
    # Save the user data into the PostgreSQL database
    cur.execute("INSERT INTO users (chat_id, whatsapp, username) VALUES (%s, %s, %s)", (user_id, whatsapp, username))
    conn.commit()

    await update.message.reply_text(f"User {username} registered successfully!")

# Handle SignIn button press: check if user exists
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Check if user exists in the database
    cur.execute("SELECT * FROM users WHERE chat_id = %s", (user_id,))
    user = cur.fetchone()

    if user:
        await update.message.reply_text("Successfully logged in!")
    else:
        await update.message.reply_text("Please sign up first.")

# Main function to start the bot
async def main():
    # Set up the Telegram bot application
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    # Add handlers for the commands and buttons
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(signup, pattern="signup"))
    app.add_handler(CallbackQueryHandler(login, pattern="signin"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_signup))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username))

    # Run the bot
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
