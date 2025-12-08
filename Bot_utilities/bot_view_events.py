import json
import os
import sys
from dotenv import load_dotenv
import httpx
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes, CallbackQueryHandler
import psycopg2
from PostgreSQL_DB.db_utilities import connect_db
from Bot_utilities.bot_auth import *

sys.dont_write_bytecode = True  # Prevent .pyc files generation

PAGE_SIZE = 3 # Number of events to fetch at every request

from datetime import datetime

def format_event(e):
    event_type = e["event_type"]
    title = e["title"]
    start_dt = datetime.fromisoformat(e["start_date_time"])
    end_dt = datetime.fromisoformat(e["end_date_time"])
    location = e["location"]
    capacity = e["capacity"]
    cost = e["cost"]

    return (
        f"📌 *{title}*\n"
        f"Type: {event_type}\n"
        f"Start: {start_dt.strftime('%d/%m/%Y %H:%M')}\n"
        f"End: {end_dt.strftime('%d/%m/%Y %H:%M')}\n"
        f"Location: {location}\n"
        f"Capacity: {capacity}\n"
        f"Cost: € {cost}\n"
    )

# Build keyboard for navigation
def events_keyboard(offset, page_size, fetched_count):
    buttons = []
    if fetched_count == page_size: # Do not show the "View More" button if less than PAGE_SIZE events are fetched
        buttons.append([InlineKeyboardButton("View More", callback_data=f"view:{offset + page_size}")])
    buttons.append([InlineKeyboardButton("Back", callback_data="back")])
    return InlineKeyboardMarkup(buttons)

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE, offset=0):
    # If this method is triggered by a callback query, extract offset
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        offset = int(query.data.split(":")[1]) if ":" in query.data else offset
        chat_id = query.message.chat_id
        await query.message.delete() # Delete previous buttons
    else:
        chat_id = update.message.chat_id

    async with httpx.AsyncClient() as client:
        load_dotenv()  # Loads variables from .env into environment
        CALENDAR_SERVICE_URL = os.environ.get("CALENDAR_SERVICE_URL")
        params = {"offset": offset}
        response = await client.get(f"{CALENDAR_SERVICE_URL}/events/view",params=params)
        if response.status_code == 200:
            events_json = response.json()  
            # If there are no more events
            if not events_json:
                await context.bot.send_message(chat_id, "No more events.")
                return
            
            # Send each event as a separate message
            for event in events_json:
                formatted_text = format_event(event)
                await context.bot.send_message(chat_id, formatted_text, parse_mode="Markdown")
            
            # Send navigation buttons ('View More' and 'Back')
            keyboard = events_keyboard(offset, PAGE_SIZE, len(events_json))
            await context.bot.send_message(chat_id, "Select on option:", reply_markup=keyboard)

        else:
            message = f"Failed to fetch events. Please try later (HTTP code: {response.status_code})"
            await context.bot.send_message(chat_id, message, parse_mode="Markdown")