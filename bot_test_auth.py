# bot_test_auth.py

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    ContextTypes, 
    MessageHandler, 
    ConversationHandler, 
    filters, 
    CallbackQueryHandler
)
import logging
import os
import sys
from datetime import date 
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
# Internal service imports
from Authentication.authentication_internal_service import register_user, authenticate_user, get_user_role, logout_user, check_session_timeout

sys.dont_write_bytecode = True
load_dotenv() 

# ==================== GLOBAL CONFIGURATION ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ==================== Conversation States ====================
# Login States
AUTH_USERNAME, AUTH_PASSWORD = range(2)

# Registration States
REG_NAME, REG_SURNAME, REG_BIRTHDATE_CALENDAR, REG_BIRTHDATE_PROCESSING, REG_ROLE, REG_USERNAME, REG_PASSWORD = range(2, 9)


# ==================== 1. /START HANDLER ====================
async def start_function(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command.
    Checks authentication status and session timeout, presenting the appropriate keyboard.
    """
    
    tg_id = update.message.from_user.id
    user_info = None
    session_expired = False

    # Check if Telegram ID exists in DB (registered user)
    initial_user_info = get_user_role(tg_id) 

    # --- 1. Prepare Keyboards based on registration status ---
    
    auth_options = [] # Will hold the list of button rows

    if not initial_user_info:
        # User is UNREGISTERED. Offer only REGISTER.
        auth_options.append([InlineKeyboardButton("Register", callback_data="register_init")])
    
    # Offer LOGIN to everyone (registered or new, if they already have credentials)
    auth_options.append([InlineKeyboardButton("Login", callback_data="login_init")])
    
    # InlineKeyboardMarkup expects a list of lists of buttons (the rows)
    auth_markup = InlineKeyboardMarkup(auth_options) 
    
    # --- 2. Check Session Timeout (only if user is registered) ---
    if initial_user_info:
        # Check session timeout (updates last_access if OK)
        session_ok = check_session_timeout(tg_id) 

        if not session_ok:
            # Session expired
            session_expired = True
            await update.message.reply_text("Your session has expired. Please login again.")
        else:
            # Session OK, user is authenticated
            user_info = initial_user_info
    
    # --- 3. Final Response ---
    if not user_info:
        # Not authenticated, not registered, or session expired.
        
        welcome_message = "Welcome! Please log in or register to continue."
        if initial_user_info and session_expired:
             welcome_message = "Your session expired. Please log in."
        elif not initial_user_info:
             welcome_message = "Welcome! You are not registered. Please register to continue."
             
        await update.message.reply_text(
            welcome_message,
            reply_markup=auth_markup
        )
    else:
        # Authenticated user: show main menu.
        role = user_info['role'].upper()
        
        # Logged-in user keyboard (includes Logout and Admin/Leader options)
        user_keyboard = [
             [InlineKeyboardButton("View Events", callback_data="events_list")],
        ]
        if role == 'ADMIN': # Admin has more options
             user_keyboard.append([InlineKeyboardButton("Check-In Scan", callback_data="admin_checkin")])
             user_keyboard.append([InlineKeyboardButton("Admin Management", callback_data="admin_user_mgmt")])
             
        # Add Logout
        user_keyboard.append([InlineKeyboardButton("Logout", callback_data="logout")])

        await update.message.reply_text(
            f"Welcome back, {user_info['name']} {user_info['surname']} (Role: {role}). Please select one of the following options:",
            reply_markup=InlineKeyboardMarkup(user_keyboard)
        )

# ==================== LOGOUT HANDLER ====================

async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles logout and invalidates the session in the DB."""
    query = update.callback_query
    await query.answer() 
    
    tg_id = query.from_user.id
    
    success = logout_user(tg_id) 

    if success:
        await query.edit_message_text("You have been successfully logged out. Type /start to login again.")
    else:
        await query.edit_message_text("Logout failed. Please try again.")

# ==================== 2. CONVERSATION INITIALIZATION ====================

async def auth_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes Login or Registration flow based on button click."""
    query = update.callback_query
    await query.answer() 
    
    if query.data == 'login_init':
        await query.edit_message_text("Please, enter your Username to log in:")
        return AUTH_USERNAME
        
    elif query.data == 'register_init':
        await query.edit_message_text("Starting Registration. Please, enter your Name:")
        return REG_NAME
        
    return ConversationHandler.END


# ==================== 3. REGISTRATION FLOW ====================

# 1. Capture Name
async def reg_capture_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['reg_name'] = update.message.text
    await update.message.reply_text("Please, enter your Surname:")
    return REG_SURNAME

# 2. Capture Surname and Show Calendar
async def reg_capture_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['reg_surname'] = update.message.text
    
    # Initialize the calendar instance
    calendar_instance = DetailedTelegramCalendar(
        locale='en', 
        min_date=date(1920, 1, 1), 
        max_date=date.today()
    )
    
    # Use the correct method to build the initial keyboard (corrected from previous error)
    calendar, step = calendar_instance.build() 
    
    await update.message.reply_text(
        "Please, select your Birthdate:",
        reply_markup=calendar
    )
    
    return REG_BIRTHDATE_CALENDAR

# 3. Process Calendar Selection
async def reg_process_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles calendar button clicks (year, month, day selection)."""
    
    query = update.callback_query
    await query.answer()
    
    # Process the calendar callback data
    result, key, step = DetailedTelegramCalendar(
        locale='en',
        min_date=date(1920, 1, 1),
        max_date=date.today()
    ).process(query.data)
    
    if not result and key:
        # Calendar step pending (year or month selected)
        await query.edit_message_text(f"Please select {LSTEP[step]}", reply_markup=key)
        return REG_BIRTHDATE_CALENDAR 
    
    elif result:
        # Day selection completed
        context.user_data['reg_birthdate'] = result.isoformat() 
        
        # Ask for Role
        role_keyboard = [
            [InlineKeyboardButton("Follower", callback_data="role_follower")],
            [InlineKeyboardButton("Leader", callback_data="role_leader")]
        ]
        
        await query.edit_message_text(
            f"Birthdate saved: {result.strftime('%Y-%m-%d')}. What is your role?", 
            reply_markup=InlineKeyboardMarkup(role_keyboard)
        )
        
        return REG_ROLE

# 4. Capture Role via Callback
async def reg_capture_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captures the role selected by the user."""
    query = update.callback_query
    await query.answer()

    chosen_role = query.data.split('_')[1] 
    context.user_data['reg_role'] = chosen_role

    await query.edit_message_text(f"Please, choose a Username (must be unique):")
    
    return REG_USERNAME


# 5. Capture Username
async def reg_capture_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captures the desired username."""
    context.user_data['reg_username'] = update.message.text
    await update.message.reply_text("Please, enter a Password:")
    return REG_PASSWORD

# 6. Capture Password and Finalize Registration
async def reg_capture_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final step: captures password, registers user in DB, and deletes the password message."""
    
    name = context.user_data.get('reg_name')
    surname = context.user_data.get('reg_surname')
    birthdate = context.user_data.get('reg_birthdate')
    role = context.user_data.get('reg_role') 
    username = context.user_data.get('reg_username')
    raw_password = update.message.text
    telegram_id = update.message.from_user.id
    
    # Delete the message containing the password immediately for privacy
    await update.message.delete()
    
    # Register the user via internal service
    registration_result = register_user(
        telegram_id, name, surname, birthdate, username, raw_password, role
    )

    if registration_result is True:
        await update.effective_chat.send_message(f"Registration complete for {username}! Role: {role.capitalize()}. Type /start.")
    else:
        await update.effective_chat.send_message(f"Registration failed: {registration_result}. Please try again with /start.")
        
    context.user_data.clear() 
    return ConversationHandler.END


# ==================== 4. LOGIN FLOW ====================

# 1. Capture Username for Login
async def auth_capture_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captures username for login."""
    context.user_data['auth_username'] = update.message.text
    await update.message.reply_text("Please, enter your Password:")
    return AUTH_PASSWORD

# 2. Capture Password and Attempt Login (MODIFICATA)
async def auth_attempt_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Attempts to authenticate the user, deletes the password message, and shows the main menu."""
    username = context.user_data.get('auth_username')
    raw_password = update.message.text
    
    # Delete the message containing the password immediately
    await update.message.delete()
    
    # Try to authenticate
    user_credentials = authenticate_user(username, raw_password) 

    if user_credentials:
        # Authentication SUCCESSFUL
        
        # user_credentials contains (telegram_id, role)
        tg_id, role = user_credentials 
        role = role.upper() # Ensure role is uppercase for menu comparison
        
        # Fetch full user details if available (get_user_role returns full info if session is OK)
        # Re-use the DB query to get name/surname for the welcome message
        user_info = get_user_role(tg_id) 

        # --- Build Logged-in Menu (Copied from start_function) ---
        user_keyboard = [
             [InlineKeyboardButton("View Events", callback_data="events_list")],
        ]
        
        # Admin options
        if role == 'ADMIN': 
             user_keyboard.append([InlineKeyboardButton("Check-In Scan", callback_data="admin_checkin")])
             user_keyboard.append([InlineKeyboardButton("Admin Management", callback_data="admin_user_mgmt")])
             
        # Add Logout
        user_keyboard.append([InlineKeyboardButton("Logout", callback_data="logout")])
        
        # Use fetched name/surname if available, otherwise use username
        name = user_info.get('name', username)
        surname = user_info.get('surname', '')
        
        await update.effective_chat.send_message(
            f"Login successful! Welcome back, {name} {surname} (Role: {role}). Please select one of the following options:",
            reply_markup=InlineKeyboardMarkup(user_keyboard)
        )
        
    else:
        # Authentication FAILED
        await update.effective_chat.send_message("Login failed. Invalid username or password. Please try /start again.")
        
    context.user_data.clear()
    return ConversationHandler.END


# ==================== 5. FALLBACKS AND CANCELLATION ====================

async def cancel_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /cancel command, ending the current conversation."""
    context.user_data.clear()
    await update.effective_chat.send_message("Operation cancelled. Type /start to begin again.")
    return ConversationHandler.END


# ==================== MAIN ====================

def main() -> None:
    """Starts the bot and adds all handlers."""
    
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set in environment variables. Exiting.")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # Main handler for start command
    app.add_handler(CommandHandler("start", start_function))
    
    # Handler for Logout callback
    app.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout$'))

    # ConversationHandler for Registration
    reg_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(auth_button_callback, pattern='^register_init$')],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_capture_name)],
            REG_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_capture_surname)],
            
            # Calendar handler (handles all steps of date selection)
            REG_BIRTHDATE_CALENDAR: [CallbackQueryHandler(reg_process_calendar)],
            
            # Role selection handler
            REG_ROLE: [CallbackQueryHandler(reg_capture_role, pattern='^role_(follower|leader)$')], 
            REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_capture_username)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_capture_password)]
        },
        fallbacks=[CommandHandler('cancel', cancel_function)]
    )
    app.add_handler(reg_conv_handler)
    
    # ConversationHandler for Login
    auth_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(auth_button_callback, pattern='^login_init$')],
        states={
            AUTH_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_capture_username)],
            AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_attempt_login)]
        },
        fallbacks=[CommandHandler('cancel', cancel_function)]
    )
    app.add_handler(auth_conv_handler)

    # Start the bot
    logging.info("Bot started and polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()