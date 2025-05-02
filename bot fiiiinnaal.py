import logging
import os
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          filters, ConversationHandler, ContextTypes)
from datetime import datetime

# === Keep-Alive Web Server ===
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run).start()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)

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

    if context.args and context.args[0] == "rating":
        if user_id in rated_users:
            await update.message.reply_text("❌ لقد قمت بتقييم البوت من قبل. شكراً!")
            return ConversationHandler.END

        context.user_data["name"] = full_name
        context.user_data["username"] = username
        context.user_data["id"] = user_id

        reply_markup = ReplyKeyboardMarkup(
            [["طب بشري", "طب اسنان"], ["صيدلة", "فرع اخر"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        await update.message.reply_text("📘 ما هو فرع دراستك؟", reply_markup=reply_markup)
        return ASK_FACULTY

    else:
        await update.message.reply_text("👋 أهلاً بك في البوت. يمكنك إرسال أي رسالة هنا للتواصل.")

async def ask_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["faculty"] = update.message.text
    reply_markup = ReplyKeyboardMarkup(
        [["2", "3", "4"], ["5", "6"]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text("📚 في أي سنة دراسية أنت؟", reply_markup=reply_markup)
    return ASK_YEAR

async def ask_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["year"] = update.message.text
    reply_markup = ReplyKeyboardMarkup(
        [["1", "2", "3"], ["4", "5"]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text("⭐ ما تقييمك للبوت من 1 إلى 5؟", reply_markup=reply_markup)
    return ASK_RATING

async def save_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data["id"]
    if user_id in rated_users:
        await update.message.reply_text("❌ لقد قمت بالتقييم مسبقاً.", reply_markup=ReplyKeyboardRemove())
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

    msg = (f"📥 تقييم جديد:\n"
           f"👤 {entry['name']} (@{entry['username']})\n"
           f"🆔 {entry['id']}\n"
           f"📚 {entry['faculty']} - سنة {entry['year']}\n"
           f"⭐ التقييم: {entry['rating']}\n🕒 {entry['time']}")
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
    await update.message.reply_text("✅ شكراً على تقييمك!", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("💬 إذا كان لديك أي اقتراح أو سؤال أو تحتاج إلى مساعدة، فقط أرسل رسالتك هنا وسنقوم بالرد عليك!")

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
        await update.message.reply_text("📩 تم استلام رسالتك، شكراً!")

    msg = f"✉️ رسالة جديدة من {full_name} (@{username})\n🆔 {user_id}\n💬 {update.message.text}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        args = context.args
        target_id = int(args[0])
        message = " ".join(args[1:])
        await context.bot.send_message(chat_id=target_id, text=message)
        await update.message.reply_text("✅ تم إرسال الرسالة.")
    except:
        await update.message.reply_text("⚠️ الصيغة الصحيحة: /reply user_id رسالتك")

async def number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"👥 عدد المستخدمين: {len(users)}")

async def allrates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        await context.bot.send_document(chat_id=ADMIN_ID, document=open("ratings.txt", "rb"))
    except:
        await update.message.reply_text("❌ لا يوجد تقييمات بعد.")

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
    app.add_handler(CommandHandler("reply", reply))
    app.add_handler(CommandHandler("number", number))
    app.add_handler(CommandHandler("allrates", allrates))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    import asyncio

    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())