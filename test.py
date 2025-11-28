from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import logging
import os
import urllib.parse

# Local auth DB helper
from auth_db import get_user, init_db

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s", level=logging.INFO
)

# Read config from environment; fallback to existing token if not set
#BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_TOKEN = "8538277966:AAG8qVFIv-7kztIIHh_yEMSNbVDIxkQl-jM"

# Base URL for the web app handling Google OAuth (set this in env for production)
WEBAPP_BASE = os.environ.get("WEBAPP_BASE", "http://localhost:5000")
AUTH_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔑 AUTHENTICATE / SIGN IN")], 
    ], 
    resize_keyboard=True, # Makes the keyboard compact
    one_time_keyboard=False # Keeps the keyboard visible
)


# Asynchronous function: only allowed if user authenticated
async def hello(update, context) -> None:
    tg_id = update.message.from_user.id
    user = get_user(tg_id)
    if not user:
        auth_link = f"{WEBAPP_BASE}/login?tg_id={urllib.parse.quote_plus(str(tg_id))}"
        await update.message.reply_text(
            "You are not authenticated. Please authenticate with Google:\n"
            + auth_link
        )
        return

    await update.message.reply_text(f"Hello, {user.get('name') or update.message.from_user.first_name} ({user.get('email')})")

async def start_function(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    
    # Send an inline "LOGIN WITH GOOGLE" button that triggers a callback
    keyboard = [
        [InlineKeyboardButton("LOGIN WITH GOOGLE", callback_data="auth")]
    ]
    keyboard_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Welcome! To get started and link your Google account, press the button below:",
        reply_markup=keyboard_markup
    )


async def auth_function(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a button with the authentication link for the user to click."""
    # Support calling /auth from both message and callback contexts
    tg_id = None
    chat_id = None
    if update.message:
        tg_id = update.message.from_user.id
        chat_id = update.message.chat_id
    elif update.callback_query:
        tg_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id

    if tg_id is None or chat_id is None:
        return

    await send_auth_link(chat_id, tg_id, context)


async def send_auth_link(chat_id: int, tg_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the authentication link to the given chat.

    If the configured `WEBAPP_BASE` is not acceptable for Telegram inline URL buttons
    (for example `localhost` or non-HTTPS), the function will send the URL as plain text
    so Telegram doesn't reject the message creation.
    """
    auth_link = f"{WEBAPP_BASE}/login?tg_id={urllib.parse.quote_plus(str(tg_id))}"
    #auth_link = "https://www.ansa.it"

    # Simple validation: avoid creating inline URL buttons for localhost/127.0.0.1 or non-HTTPS
    parsed = urllib.parse.urlparse(auth_link)
    hostname = parsed.hostname or ""
    url_allowed = parsed.scheme == "https" and hostname not in ("localhost", "127.0.0.1")

    if url_allowed:
        keyboard = [[InlineKeyboardButton("🔗 Sign in with Google", url=auth_link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text="Please click the button below to sign in with Google and link your account:",
            reply_markup=reply_markup,
        )
    else:
        # Fall back to sending the raw link as text (works for local testing / ngrok users)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Please open the following link in your browser to sign in and link your account:\n"
                + auth_link
            ),
        )
    


async def callback_handler(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks. Currently supports the 'auth' callback which
    triggers sending the authentication link (same effect as /auth).
    """
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if query.data == "auth":
        tg_id = query.from_user.id
        chat_id = query.message.chat_id
        await send_auth_link(chat_id, tg_id, context)


def main() -> None:
    # Ensure DB exists
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_function))
    app.add_handler(CommandHandler("ciao", hello))
    app.add_handler(CommandHandler("auth", auth_function))
    app.add_handler(CallbackQueryHandler(callback=callback_handler))
    app.run_polling()


if __name__ == "__main__":
    main()