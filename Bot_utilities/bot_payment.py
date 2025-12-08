from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes,ContextTypes
from Payments.payment_functions import test_paypal

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

async def pay_function(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = None
    if update.message:
        tg_id = update.message.from_user.id
        chat_id = update.message.chat_id
    elif update.callback_query:
        tg_id = update.callback_query.from_user.id
        chat_id = update.callback_query.message.chat_id

    linkToBeReturned = test_paypal()
    keyboard = [[InlineKeyboardButton("🔗 Complete the payment", url=linkToBeReturned)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    #print("RETURNED LINK: "+linkToBeReturned)
    await context.bot.send_message(
        chat_id=chat_id,
        text="Please click here to complete the payment:",
        reply_markup=reply_markup,
    )