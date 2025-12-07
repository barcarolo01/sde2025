from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    ConversationHandler, filters, CallbackQueryHandler
)
import logging
import os
import sys
import requests
from datetime import date
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

sys.dont_write_bytecode = True
load_dotenv()

# ------------------------------
# CONFIG
# ------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GESTIONE_UTENTI_URL = os.getenv("GESTIONE_UTENTI_URL")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

AUTH_USERNAME, AUTH_PASSWORD = range(2)
REG_NAME, REG_SURNAME, REG_BIRTHDATE_CALENDAR, REG_ROLE, REG_USERNAME, REG_PASSWORD = range(2, 8)


# ------------------------------
# START COMMAND
# ------------------------------
async def start_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Register", callback_data="register_init")],
        [InlineKeyboardButton("Login", callback_data="login_init")]
    ]

    await update.message.reply_text(
        "Welcome! Please login or register:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ------------------------------
# LOGOUT
# ------------------------------
async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("You are now logged out. Type /start to begin.")


# ------------------------------
# AUTH / REGISTER INIT
# ------------------------------
async def auth_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "login_init":
        await query.edit_message_text("Enter your username:")
        return AUTH_USERNAME

    if query.data == "register_init":
        await query.edit_message_text("Enter your Name:")
        return REG_NAME


# ------------------------------
# REGISTRATION FLOW
# ------------------------------
async def reg_name(update, context):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Enter your Surname:")
    return REG_SURNAME


async def reg_surname(update, context):
    context.user_data["surname"] = update.message.text

    calendar, step = DetailedTelegramCalendar(
        locale="en",
        min_date=date(1920, 1, 1),
        max_date=date.today()
    ).build()

    await update.message.reply_text("Select Birthdate:", reply_markup=calendar)
    return REG_BIRTHDATE_CALENDAR


async def reg_calendar(update, context):
    query = update.callback_query
    await query.answer()

    result, key, step = DetailedTelegramCalendar(
        locale="en",
        min_date=date(1920, 1, 1),
        max_date=date.today()
    ).process(query.data)

    if not result and key:
        await query.edit_message_text(f"Select {LSTEP[step]}", reply_markup=key)
        return REG_BIRTHDATE_CALENDAR

    if result:
        context.user_data["birthdate"] = result.isoformat()

        keyboard = [
            [InlineKeyboardButton("Follower", callback_data="role_follower")],
            [InlineKeyboardButton("Leader", callback_data="role_leader")]
        ]

        await query.edit_message_text(
            f"Birthdate saved: {result}. Select your role:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return REG_ROLE


async def reg_role(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["role"] = query.data.split("_")[1]
    await query.edit_message_text("Choose a Username:")
    return REG_USERNAME


async def reg_username(update, context):
    context.user_data["username"] = update.message.text
    await update.message.reply_text("Enter a Password:")
    return REG_PASSWORD


async def reg_password(update, context):
    tg_id = update.message.from_user.id
    password = update.message.text
    await update.message.delete()

    payload = {
        "action": "register",
        "telegram_id": tg_id,
        "name": context.user_data["name"],
        "surname": context.user_data["surname"],
        "birthdate": context.user_data["birthdate"],
        "username": context.user_data["username"],
        "password": password,
        "role": context.user_data["role"]
    }

    try:
        resp = requests.post(f"{GESTIONE_UTENTI_URL}/register", json=payload)

        if resp.status_code == 200:
            await update.effective_chat.send_message("Registration complete! Type /start.")
        else:
            await update.effective_chat.send_message(f"Registration failed: {resp.text}")

    except Exception as e:
        await update.effective_chat.send_message(f"Service error: {e}")

    context.user_data.clear()
    return ConversationHandler.END


# ------------------------------
# LOGIN FLOW
# ------------------------------
async def auth_username(update, context):
    context.user_data["auth_username"] = update.message.text
    await update.message.reply_text("Enter your Password:")
    return AUTH_PASSWORD


async def auth_attempt_login(update, context):
    username = context.user_data["auth_username"]
    password = update.message.text
    await update.message.delete()

    payload = {
        "action": "login",
        "telegram_id": update.message.from_user.id,
        "username": username,
        "password": password
    }

    try:
        resp = requests.post(f"{GESTIONE_UTENTI_URL}/login", json=payload)

        if resp.status_code == 200:
            data = resp.json()
            role = data["role"].upper()

            keyboard = [[InlineKeyboardButton("Logout", callback_data="logout")]]

            await update.effective_chat.send_message(
                f"Welcome back {data['name']} {data['surname']} (Role: {role})",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.effective_chat.send_message("Login failed.")

    except Exception as e:
        await update.effective_chat.send_message(f"Service error: {e}")

    context.user_data.clear()
    return ConversationHandler.END


# ------------------------------
# MAIN
# ------------------------------
def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN missing")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_function))
    app.add_handler(CallbackQueryHandler(logout_callback, pattern="^logout$"))

    registration = ConversationHandler(
        entry_points=[CallbackQueryHandler(auth_button_callback, pattern="^register_init$")],
        states={
            REG_NAME: [MessageHandler(filters.TEXT, reg_name)],
            REG_SURNAME: [MessageHandler(filters.TEXT, reg_surname)],
            REG_BIRTHDATE_CALENDAR: [CallbackQueryHandler(reg_calendar)],
            REG_ROLE: [CallbackQueryHandler(reg_role)],
            REG_USERNAME: [MessageHandler(filters.TEXT, reg_username)],
            REG_PASSWORD: [MessageHandler(filters.TEXT, reg_password)]
        },
        fallbacks=[]
    )

    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(auth_button_callback, pattern="^login_init$")],
        states={
            AUTH_USERNAME: [MessageHandler(filters.TEXT, auth_username)],
            AUTH_PASSWORD: [MessageHandler(filters.TEXT, auth_attempt_login)]
        },
        fallbacks=[]
    )

    app.add_handler(registration)
    app.add_handler(login_conv)

    app.run_polling()


if __name__ == "__main__":
    main()
