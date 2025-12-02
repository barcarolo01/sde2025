from dotenv import load_dotenv
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes,CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters,CallbackQueryHandler
import logging
import os
import sys
import Payments.payment_functions as payment_functions
from Database.auth_db import init_db, insert_user, get_user

sys.dont_write_bytecode = True  # Prevent .pyc files generation
load_dotenv()  # Loads variables from .env into environment

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s", level=logging.INFO
)

# Read config from environment; fallback to existing token if not set
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBAPP_BASE = os.environ.get("WEBAPP_BASE", "https://sde2025.onrender.com")

# ==================== Start ====================
async def start_function(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.message.from_user.id
    user = get_user(tg_id)
    if not user: # If the user is not authenticated
        # Send an inline "Login with Google" button that triggers a callback
        keyboard = [
            [InlineKeyboardButton("Register Now!", callback_data="auth")],
        ]
        keyboard_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Welcome! It seems you are not authenticated. To get started, please register by clicking the button below:",
            reply_markup=keyboard_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Buy a lesson", callback_data="pay")],
            [InlineKeyboardButton("Function2", callback_data="f1")],
            [InlineKeyboardButton("Function3", callback_data="f2")]
        ]
        keyboard_markup = InlineKeyboardMarkup(keyboard)
        

        await update.message.reply_text(
            f"Welcome {user.get('name')}. Please select one of the following options:",
            reply_markup=keyboard_markup
        )

async def pay_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "pay":
        # IMPORTANT: pay_function expects an Update containing a .message
        # but button presses come as a callback_query.
        # So we call it manually using the callback's message.
        fake_update = Update(
            update.update_id,
            message=query.message
        )
        return await pay_function(fake_update, context)


# ==================== Registration and authentication ====================
NAME, SURNAME = range(2)

async def auth_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter your **name**:")
    return NAME

async def auth_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    if query.data == 'auth':
        await query.message.reply_text("Please enter your *name*:")
        return NAME
    


# Capture name
async def capture_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Please enter your **surname**:")
    return SURNAME

# Capture surname and save the user in the DB
async def capture_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data['name']
    surname = update.message.text
    telegram_id = update.message.from_user.id
    insert_user(telegram_id,name,surname,"customer") # By default, a just-registered user is a customer

    await update.message.reply_text(f"Thank you {name} {surname}! You are now registered.")
    return ConversationHandler.END

# Cancel handler
async def cancel_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END


# ==================== Payments ====================
async def pay_function(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = None
    if update.message:
        tg_id = update.message.from_user.id
        chat_id = update.message.chat_id
    elif update.callback_query:
        tg_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id

    linkToBeReturned = payment_functions.test_paypal()
    keyboard = [[InlineKeyboardButton("🔗 Complete the payment", url=linkToBeReturned)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    print("RETURNED LINK: "+linkToBeReturned)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Please click here to complete the payment:",
        reply_markup=reply_markup,
    )

def main() -> None:
    # Ensure DB exists
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_function))

    # Handler for authentication services
    app.add_handler(CommandHandler("auth", auth_function))

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(auth_button_callback, pattern='^auth$')],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_name)],
            SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_surname)]
        },
        fallbacks=[CommandHandler('cancel', cancel_function)]
    )
    app.add_handler(conv_handler)

    # Handler for payment services
    app.add_handler(CommandHandler("pay", pay_function))
    app.add_handler(CallbackQueryHandler(pay_button_callback, pattern="^pay$"))

    # Polling (Waiting for requests)
    app.run_polling()

if __name__ == "__main__":
    main()