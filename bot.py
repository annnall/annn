import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from datetime import datetime

BOT_TOKEN = os.getenv("7978684973:AAFFf474iWrfEjiAIk_ZOqWl6ABznMBIe4o")
ADMIN_ID = int(os.getenv("645421401"))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

ASK_FACULTY, ASK_YEAR, ASK_RATING = range(3)

users = {}
ratings = []
first_messages = set()
rated_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "(no username)"
    full_name = f"{user.first_name} {user.last_name or ''}".strip()

    if user_id not in users:
        users[user_id] = {
            "name": full_name,
            "username": username,
            "id": user_id,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    if user_id in rated_users:
        await update.message.reply_text("❌ You already submitted a rating. Thank you!")
        return ConversationHandler.END

    context.user_data["name"] = full_name
    context.user_data["username"] = username
    context.user_data["id"] = user_id

    reply_markup = ReplyKeyboardMarkup(
        [["Medicine", "Dentistry"], ["Pharmacy", "Other"]],
        one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text("🧑‍⚕️ What are you studying?", reply_markup=reply_markup)
    return ASK_FACULTY

async def ask_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["faculty"] = update.message.text
    reply_markup = ReplyKeyboardMarkup(
        [["2", "3", "4", "5"]],
        one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text("📚 Which year are you in?", reply_markup=reply_markup)
    return ASK_YEAR

async def ask_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["year"] = update.message.text
    reply_markup = ReplyKeyboardMarkup(
        [["0", "1", "2", "3", "4", "5"]],
        one_time_keyboard=True, resize_keyboard=True
    )
    await update.message.reply_text("⭐ What’s your rating out of 5?", reply_markup=reply_markup)
    return ASK_RATING

async def save_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data["id"]
    if user_id in rated_users:
        await update.message.reply_text("❌ You already submitted a rating.")
        return ConversationHandler.END

    context.user_data["rating"] = update.message.text
    entry = {
        "name": context.user_data["name"],
        "username": context.user_data["username"],
        "id": user_id,
        "faculty": context.user_data["faculty"],
        "year": context.user_data["year"],
        "rating": context.user_data["rating"],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    ratings.append(entry)
    rated_users.add(user_id)

    with open("ratings.txt", "a") as file:
        file.write(f"{entry}\n")

    msg = (f"📥 New Rating Received:\n"
           f"👤 {entry['name']} (@{entry['username']})\n"
           f"🆔 {entry['id']}\n"
           f"📚 {entry['faculty']} - Year {entry['year']}\n"
           f"⭐ Rating: {entry['rating']}\n🕒 {entry['time']}")
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
    await update.message.reply_text("✅ Thank you for your feedback!")
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "(no username)"
    full_name = f"{user.first_name} {user.last_name or ''}".strip()

    if user_id not in users:
        users[user_id] = {
            "name": full_name,
            "username": username,
            "id": user_id,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    if user_id not in first_messages:
        first_messages.add(user_id)
        await update.message.reply_text("📩 Got your message")

    msg = f"✉️ New message from {full_name} (@{username})\n🆔 {user_id}\n💬 {update.message.text}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_FACULTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_year)],
            ASK_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rating)],
            ASK_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_rating)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

if __name__ == "__main__":
    import os
    import asyncio
    asyncio.run(main())