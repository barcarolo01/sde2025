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
import requests # Used for making REST API calls (login, register, validate, logout)
import logging
import os
import sys
from datetime import date 
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

sys.dont_write_bytecode = True
load_dotenv() # Load environment variables from .env file

# ==================== GLOBAL CONFIGURATION ====================
# Set up basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Base URL for the external Authentication API
AUTH_API_URL = os.environ.get("AUTH_API_URL") 

# ==================== Conversation States ====================
# States for the Login Conversation Flow
AUTH_USERNAME, AUTH_PASSWORD = range(2)

# States for the Registration Conversation Flow (starting from 2 to avoid collision)
REG_NAME, REG_SURNAME, REG_BIRTHDATE_CALENDAR, REG_BIRTHDATE_PROCESSING, REG_ROLE, REG_USERNAME, REG_PASSWORD = range(2, 9)


# ==================== 1. /START HANDLER (Session Check) ====================

async def start_function(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks the session status (auth token) via REST API and displays the appropriate menu (Login/Register or Main Menu)."""
    
    if update.message is None:
        return

    # 1. Try to retrieve the stored token from the user's session data
    token = context.user_data.get('auth_token')
    user_info = None

    if token:
        # --- REST CALL: /validate (Verify the token's validity) ---
        try:
            response = requests.post(
                f"{AUTH_API_URL}/validate",
                json={"token": token}
            )
            
            if response.status_code == 200:
                # Token is valid and not expired
                user_info = response.json()
            else:
                # Token is invalid or expired (e.g., 401 Unauthorized)
                user_info = None
                context.user_data.clear() # Clear the invalid local token
                
        except requests.exceptions.RequestException:
            # Handle connection errors to the auth service
            await update.message.reply_text("Connection error to the authentication service. Please try again later.")
            return 
    
    # --- 2. Prepare and show the keyboard menus ---
    if not user_info:
        # User is NOT authenticated: show Login/Register options
        auth_options = [
            [InlineKeyboardButton("Register", callback_data="register_init")],
            [InlineKeyboardButton("Login", callback_data="login_init")]
        ]
        auth_markup = InlineKeyboardMarkup(auth_options) 
        
        await update.message.reply_text(
            "Welcome! Please log in or register to continue.",
            reply_markup=auth_markup
        )
    else:
        # User IS authenticated with a valid Token: show main menu based on role
        role = user_info['role'].upper()
        
        user_keyboard = [
             [InlineKeyboardButton("View Events", callback_data="events_list")],
        ]
        
        if role == 'ADMIN': 
             # Add admin-specific options
             user_keyboard.append([InlineKeyboardButton("Check-In Scan", callback_data="admin_checkin")])
             user_keyboard.append([InlineKeyboardButton("Admin Management", callback_data="admin_user_mgmt")])
             
        user_keyboard.append([InlineKeyboardButton("Logout", callback_data="logout")])

        await update.message.reply_text(
            f"Welcome back, {user_info['name']} {user_info['surname']} (Role: {role}). Please select one of the following options:",
            reply_markup=InlineKeyboardMarkup(user_keyboard)
        )

# ==================== LOGOUT HANDLER (Invalidate Token) ====================

async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles logout by calling the REST API to invalidate the token."""
    query = update.callback_query
    await query.answer() # Acknowledge the button click
    
    token = context.user_data.get('auth_token')
    
    if not token:
        await query.edit_message_text("You are already logged out. Type /start.")
        context.user_data.clear()
        return

    # --- REST CALL: Logout ---
    try:
        # POST to /logout with the token in the JSON body
        response = requests.post(
            f"{AUTH_API_URL}/logout", 
            json={"token": token}
        )
        
        # We consider logout successful if API returns 200 or 404 (token already gone)
        if response.status_code == 200 or response.status_code == 404:
             await query.edit_message_text("You have been successfully logged out. Type /start to login again.")
        else:
             await query.edit_message_text(f"Logout failed. API returned status code {response.status_code}. Please try again.")
    
    except requests.exceptions.RequestException:
        await query.edit_message_text("Connection error to the authentication service. Please try again later.")
    
    # Always clean up the local token and user data
    context.user_data.clear() 


# ==================== 2. CONVERSATION INITIALIZATION ====================

async def auth_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes Login or Registration flow based on button click from /start menu."""
    query = update.callback_query
    await query.answer() 
    
    if query.data == 'login_init':
        await query.edit_message_text("Please, enter your Username to log in:")
        return AUTH_USERNAME # Go to the first state of the Login flow
        
    elif query.data == 'register_init':
        await query.edit_message_text("Starting Registration. Please, enter your Name:")
        return REG_NAME # Go to the first state of the Registration flow
        
    return ConversationHandler.END


# ==================== 3. REGISTRATION FLOW ====================

async def reg_capture_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves Name and asks for Surname."""
    context.user_data['reg_name'] = update.message.text
    await update.message.reply_text("Please, enter your Surname:")
    return REG_SURNAME

async def reg_capture_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves Surname and shows the Date Picker Calendar."""
    context.user_data['reg_surname'] = update.message.text
    
    # Initialize the calendar instance
    calendar_instance = DetailedTelegramCalendar(
        locale='en', 
        min_date=date(1920, 1, 1), 
        max_date=date.today()
    )
    
    calendar, step = calendar_instance.build() 
    
    await update.message.reply_text(
        "Please, select your Birthdate:",
        reply_markup=calendar
    )
    
    return REG_BIRTHDATE_CALENDAR

async def reg_process_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the calendar callback, step by step until a date is selected."""
    query = update.callback_query
    await query.answer()
    
    # Process the calendar step
    result, key, step = DetailedTelegramCalendar(
        locale='en',
        min_date=date(1920, 1, 1),
        max_date=date.today()
    ).process(query.data)
    
    if not result and key:
        # Continue to the next step (e.g., selecting month or day)
        await query.edit_message_text(f"Please select {LSTEP[step]}", reply_markup=key)
        return REG_BIRTHDATE_CALENDAR 
    
    elif result:
        # Date selection is complete
        context.user_data['reg_birthdate'] = result.isoformat() 
        
        role_keyboard = [
            [InlineKeyboardButton("Follower", callback_data="role_follower")],
            [InlineKeyboardButton("Leader", callback_data="role_leader")]
        ]
        
        await query.edit_message_text(
            f"Birthdate saved: {result.strftime('%Y-%m-%d')}. What is your role?", 
            reply_markup=InlineKeyboardMarkup(role_keyboard)
        )
        
        return REG_ROLE # Move to role selection

async def reg_capture_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the chosen role and asks for a Username."""
    query = update.callback_query
    await query.answer()

    chosen_role = query.data.split('_')[1] # Extracts 'follower' or 'leader'
    context.user_data['reg_role'] = chosen_role

    await query.edit_message_text(f"Please, choose a Username (must be unique):")
    
    return REG_USERNAME

async def reg_capture_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves Username and asks for a Password."""
    context.user_data['reg_username'] = update.message.text
    await update.message.reply_text("Please, enter a Password:")
    return REG_PASSWORD


async def reg_capture_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final step: captures password and registers user via REST API /register."""
    
    data_to_send = {
        'telegram_id': update.message.from_user.id,
        'name': context.user_data.get('reg_name'),
        'surname': context.user_data.get('reg_surname'),
        'birthdate': context.user_data.get('reg_birthdate'),
        'role': context.user_data.get('reg_role'), 
        'username': context.user_data.get('reg_username'),
        'password': update.message.text # The actual password
    }
    
    # Delete the message containing the password for security
    await update.message.delete()
    
    try:
        # POST the registration data to the external API
        response = requests.post(f"{AUTH_API_URL}/register", json=data_to_send)

        if response.status_code == 201: # 201 Created is the success code
            await update.effective_chat.send_message(f"Registration complete for {data_to_send['username']}! Role: {data_to_send['role'].capitalize()}. Type /start.")
        else:
            # Handle API-side registration failure (e.g., username already exists)
            error_msg = response.json().get('error', 'Registration failed due to server error.')
            await update.effective_chat.send_message(f"Registration failed: {error_msg}. Please try again with /start.")
            
    except requests.exceptions.RequestException:
        await update.effective_chat.send_message("Authentication service unavailable. Please try /start.")

    # Clean up the temporary registration data
    context.user_data.clear() 
    return ConversationHandler.END


# ==================== 4. LOGIN FLOW ====================

async def auth_capture_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the entered username for login and asks for the password."""
    context.user_data['auth_username'] = update.message.text
    await update.message.reply_text("Please, enter your Password:")
    return AUTH_PASSWORD

async def auth_attempt_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Attempts to authenticate the user via REST API /login, saves the token, and shows the main menu."""
    
    login_data = {
        "username": context.user_data.get('auth_username'),
        "password": update.message.text
    }
    
    # Delete the message containing the password for security
    await update.message.delete()
    
    # --- REST CALL: Login ---
    try:
        response = requests.post(
            f"{AUTH_API_URL}/login",
            json=login_data
        )

        if response.status_code == 200:
            # Authentication SUCCESSFUL
            data = response.json()
            
            # --- LOCAL TOKEN STORAGE ---
            # Save the received authentication token for future requests
            context.user_data['auth_token'] = data.get('token') 
            
            role = data.get('role').upper() 
            name = data.get('name')
            surname = data.get('surname')
            
            # --- Build Logged-in Menu ---
            user_keyboard = [
                 [InlineKeyboardButton("View Events", callback_data="events_list")],
            ]
            
            if role == 'ADMIN': 
                 # Add admin options
                 user_keyboard.append([InlineKeyboardButton("Check-In Scan", callback_data="admin_checkin")])
                 user_keyboard.append([InlineKeyboardButton("Admin Management", callback_data="admin_user_mgmt")])
                 
            user_keyboard.append([InlineKeyboardButton("Logout", callback_data="logout")])
            
            await update.effective_chat.send_message(
                f"Login successful! Welcome back, {name} {surname} (Role: {role}). Please select one of the following options:",
                reply_markup=InlineKeyboardMarkup(user_keyboard)
            )
            
        else:
            # Authentication FAILED (e.g., 401 Unauthorized)
            error_msg = response.json().get('error', 'Invalid username or password.')
            await update.effective_chat.send_message(f"Login failed. {error_msg}. Please try /start again.")
            
    except requests.exceptions.RequestException:
        await update.effective_chat.send_message("Authentication service unavailable. Please try /start.")
        
    # Clear temporary login data
    context.user_data.clear()
    return ConversationHandler.END


# ==================== 5. FALLBACKS AND CANCELLATION ====================

async def cancel_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /cancel command, ending the current conversation flow."""
    context.user_data.clear()
    await update.effective_chat.send_message("Operation cancelled. Type /start to begin again.")
    return ConversationHandler.END


# ==================== MAIN ====================

def main() -> None:
    """Starts the bot and adds all handlers (Command, CallbackQuery, and Conversation)."""
    
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set in environment variables. Exiting.")
        sys.exit(1)

    # Build the Application
    app = Application.builder().token(BOT_TOKEN).build()

    # Add main command handler
    app.add_handler(CommandHandler("start", start_function))
    
    # Add handler for the global logout button
    app.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout$'))

    # Registration Conversation Handler
    reg_conv_handler = ConversationHandler(
        # Entry point: when 'register_init' button is clicked
        entry_points=[CallbackQueryHandler(auth_button_callback, pattern='^register_init$')],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_capture_name)],
            REG_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_capture_surname)],
            
            REG_BIRTHDATE_CALENDAR: [CallbackQueryHandler(reg_process_calendar)],
            
            REG_ROLE: [CallbackQueryHandler(reg_capture_role, pattern='^role_(follower|leader)$')], 
            REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_capture_username)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_capture_password)]
        },
        # Fallback to cancel the conversation
        fallbacks=[CommandHandler('cancel', cancel_function)]
    )
    app.add_handler(reg_conv_handler)
    
    # Login Conversation Handler
    auth_conv_handler = ConversationHandler(
        # Entry point: when 'login_init' button is clicked
        entry_points=[CallbackQueryHandler(auth_button_callback, pattern='^login_init$')],
        states={
            AUTH_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_capture_username)],
            AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_attempt_login)]
        },
        # Fallback to cancel the conversation
        fallbacks=[CommandHandler('cancel', cancel_function)]
    )
    app.add_handler(auth_conv_handler)

    logging.info("Bot started and polling...")
    # Start the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()