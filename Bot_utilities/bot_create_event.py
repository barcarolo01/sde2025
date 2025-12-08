import os
import sys
import re
from dotenv import load_dotenv
import httpx
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes,ConversationHandler, ContextTypes
from telegram_bot_calendar import DetailedTelegramCalendar

from Bot_utilities.bot_auth import *

sys.dont_write_bytecode = True  # Prevent .pyc files generation

# ---- STATES ----
(
    EVENT_TYPE,
    TITLE,
    START_DATE,
    START_TIME,
    END_DATE,
    END_TIME,
    LOCATION,
    CAPACITY,
    COST,
    IS_ACTIVE,
) = range(10)  # Incremented by 1 for the new state

# Check (using Regex) if the time format is valid (HH:MM with HH in 00-23 and MM in 00-59)
def is_valid_time(time_str):
    pattern = r'^([01]?\d|2[0-3]):([0-5]\d)$' 
    return re.match(pattern, time_str) is not None

# ---- COMMAND HANDLER ----
async def start_create_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await IsUserAuthorized(update, context):
        # Build the inline keyboard for event type selection
        keyboard = [
            [
                InlineKeyboardButton("Serata", callback_data="serata"),
                InlineKeyboardButton("Porta Party", callback_data="porta_party"),
                InlineKeyboardButton("Workshop", callback_data="workshop"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Select the type of the event:",
            reply_markup=reply_markup
        )
        return EVENT_TYPE
    else:
        await update.message.reply_text("You are not authorized to perform this action.")

# ---- CALLBACK HANDLER FOR EVENT TYPE ----
async def get_event_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    # Save event type
    context.user_data["event_type"] = query.data

    # Ask for the title next
    await query.edit_message_text("Enter event title:")
    return TITLE

# ---- TITLE ----
async def get_title(update, context):
    context.user_data["title"] = update.message.text
    calendar, step = DetailedTelegramCalendar().build()
    await update.message.reply_text("Select START DATE:", reply_markup=calendar)
    return START_DATE


# ---- START DATE (calendar widget) ----
async def start_date_handler(update, context):
    result, key, step = DetailedTelegramCalendar().process(update.callback_query.data)

    if not result and key:
        await update.callback_query.message.edit_text("Select START DATE:", reply_markup=key)
        return START_DATE

    context.user_data["start_date"] = result
    await update.callback_query.message.edit_text(f"Start date: {result}")
    await update.callback_query.message.reply_text(
        "Enter START TIME (hh:mm, 24-hour format):"
    )
    return START_TIME

# ---- START TIME ----
async def start_time_handler(update, context):
    time_str = update.message.text.strip()
    if not is_valid_time(time_str):
        await update.message.reply_text(
            "❌ Invalid time. Please enter time in hh:mm format (00:00 - 23:59):"
        )
        return START_TIME

    context.user_data["start_time"] = time_str

    calendar, step = DetailedTelegramCalendar().build()
    await update.message.reply_text("Select END DATE:", reply_markup=calendar)
    return END_DATE

# ---- END DATE ----
async def end_date_handler(update, context):
    result, key, step = DetailedTelegramCalendar().process(update.callback_query.data)

    if not result and key:
        await update.callback_query.message.edit_text("Select END DATE:", reply_markup=key)
        return END_DATE

    context.user_data["end_date"] = result
    await update.callback_query.message.edit_text(f"End date: {result}")
    await update.callback_query.message.reply_text(
        "Enter END TIME (hh:mm, 24-hour format):"
    )
    return END_TIME

# ---- END TIME ----
async def end_time_handler(update, context):
    time_str = update.message.text.strip()
    if not is_valid_time(time_str):
        await update.message.reply_text(
            "❌ Invalid time. Please enter time in hh:mm format (00:00 - 23:59):"
        )
        return END_TIME

    context.user_data["end_time"] = time_str
    await update.message.reply_text("Enter location:")
    return LOCATION

# ---- LOCATION ----
async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["location"] = update.message.text
    await update.message.reply_text("Enter capacity (integer):")
    return CAPACITY

# ---- CAPACITY ----
async def get_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["capacity"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid INTEGER:")
        return CAPACITY

    await update.message.reply_text("Enter cost (float):")
    return COST

# ---- COST ----
async def get_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["cost"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid NUMBER:")
        return COST

    # Ask yes/no for is_active
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Yes", callback_data="True"),
         InlineKeyboardButton("No", callback_data="False")]
    ])
    await update.message.reply_text("Is the event active?", reply_markup=keyboard)
    return IS_ACTIVE

# ---- IS ACTIVE ----
async def get_is_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["is_active"] = (update.callback_query.data == "True")
    data = context.user_data

    # Creating a json file with the information about the event
    event_payload = {
        'event_type': data['event_type'],
        "title": data['title'],
        "start_date": f"{data['start_date']}",
        "start_time": f"{data['start_time']}",
        "end_date": f"{data['end_date']}",
        "end_time": f"{data['end_time']}",
        "location": data['location'],
        "capacity": data['capacity'],
        "cost": data['cost'],
        "is_active": data['is_active'],
    }

    # Perform HTTP POST request to Calendar service
    async with httpx.AsyncClient() as client:
        load_dotenv()  # Loads variables from .env into environment
        CALENDAR_SERVICE_URL = os.environ.get("CALENDAR_SERVICE_URL")
        response = await client.post(f"{CALENDAR_SERVICE_URL}/events/create",json=event_payload)

        if response.status_code == 200 or response.status_code == 201: # HTTP OK or HTTP Created
            summary = (
                f"*Event created:*\n\n"
                f"Event type: {data['event_type']}\n"
                f"Title: {data['title']}\n"
                f"Start: {data['start_date']} {data['start_time']}\n"
                f"End: {data['end_date']} {data['end_time']}\n"
                f"Location: {data['location']}\n"
                f"Capacity: {data['capacity']}\n"
                f"Cost: € {data['cost']}\n"
                f"Active: {data['is_active']}"
            )
            await update.callback_query.message.edit_text(summary, parse_mode="Markdown")
            return ConversationHandler.END
        else:
            print(f"Failed to create event. Please try later (HTTP code: {response.status_code})")
            return ConversationHandler.END