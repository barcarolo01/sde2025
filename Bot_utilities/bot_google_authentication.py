import os
import secrets
from dotenv import load_dotenv
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes,ContextTypes

load_dotenv()  # Loads variables from .env into environment
LOGIN_BASE_URL = os.environ.get("LOGIN_BASE_URL")

async def start_google(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id = user.id

    # Generate a random state token (CSRF protection)
    state_token = secrets.token_urlsafe(32)

    # Store mapping (so backend can later resolve the Telegram user)
    #pending_states[state_token] = tg_id

    # Build full login URL
    login_url = f"{LOGIN_BASE_URL}/login?state={state_token}&tg_id={tg_id}"

    # Create the inline button
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Login with Google", url=login_url)
    ]])

    await update.message.reply_text(
        "Click the button below to log in with Google:",
        reply_markup=keyboard
    )

