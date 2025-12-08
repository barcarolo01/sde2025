from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CommandHandler, MessageHandler, ConversationHandler, filters,CallbackQueryHandler
import logging
import os
import sys
from Bot_utilities.bot_create_event import *
from Bot_utilities.bot_view_events import *
from Bot_utilities.bot_payment import *
from Bot_utilities.bot_google_authentication import *

pending_states = {}   # state_token → tg_id
sys.dont_write_bytecode = True  # Prevent .pyc files generation
load_dotenv()  # Loads variables from .env into environment

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s", level=logging.INFO
)

# Read config from environment; fallback to existing token if not set
BOT_TOKEN = os.environ.get("BOT_TOKEN")

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("startGoogle", start_google))

    # Handler for payment services
    app.add_handler(CommandHandler("pay", pay_function))
    app.add_handler(CallbackQueryHandler(pay_button_callback, pattern="^pay$"))

    # Handler for event creation
    conv_handler_event_creation = ConversationHandler(
        entry_points=[CommandHandler("createEvent", start_create_event)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            START_DATE: [CallbackQueryHandler(start_date_handler)],
            START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_time_handler)],
            END_DATE: [CallbackQueryHandler(end_date_handler)],
            END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_time_handler)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            CAPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_capacity)],
            COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cost)],
            IS_ACTIVE: [CallbackQueryHandler(get_is_active)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_handler_event_creation)

    # Handler for event visualization
    app.add_handler(CommandHandler("viewEvents", view))
    app.add_handler(CallbackQueryHandler(view, pattern=r"^view:\d+$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.message.delete(), pattern="back"))

    app.add_handler(CallbackQueryHandler(see_more_callback, pattern="^see_more:"))


    # Polling (Waiting for requests)
    app.run_polling()


if __name__ == "__main__":
    main()