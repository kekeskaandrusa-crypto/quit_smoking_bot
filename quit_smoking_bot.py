from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime

from database import init_db, get_user, update_user, add_mark

# Токен бота вставлено
TOKEN = "8494695438:AAGhWgVDDfXf3eRkxpbOcyYd9Yc956ZPgcU"

EMOJI_FIRE = "\U0001F525"
EMOJI_MONEY = "\U0001F4B0"
EMOJI_CALENDAR = "\U0001F4C5"
EMOJI_CHECK = "\u2705"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)
    await update.message.reply_text(
        "Привіт! Я бот для відміток 'не курив'.\n"
        "Встанови ціну пачки: /setprice 90\n"
        "Відмічатися — /mark\n"
        "Статистика — /stats\n"
        "Скинути — /reset"
    )

async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Введи ціну: /setprice 90")
        return

    try:
        price = int(context.args[0])
    except:
        await update.message.reply_text("Має бути число. Наприклад: /setprice 90")
        return

    update_user(user_id, price=price)
    await update.message.reply_text(f"{EMOJI_CHECK} Ціна пачки встановлена: {price} грн")

async def mark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    today = datetime.now().strftime("%Y-%m-%d")
    last_date = user[2]
    streak = user[3] or 0

    if last_date == today:
        await update.message.reply_text("Ти вже відмічався сьогодні.")
        return

    if last_date is None:
        streak = 1
    else:
        last_dt = datetime.strptime(last_date, "%Y-%m-%d")
        delta = (datetime.now() - last_dt).days
        if delta == 1:
            streak += 1
        else:
            streak = 1

    update_user(user_id, last_date=today, streak=streak)
    add_mark(user_id, today)

    await update.message.reply_text(f"{EMOJI_CHECK} Відмічено. Серія: {EMOJI_FIRE} {streak} днів.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    price = user[1] or 0
    streak = user[3] or 0
    money = price * streak
    last_date = user[2] or "ще не відмічався"

    msg = (
        f"{EMOJI_FIRE} <b>Серія:</b> <b>{streak} днів</b>\n"
        f"{EMOJI_MONEY} <b>Зекономлено:</b> <b>{money} грн</b>\n"
        f"{EMOJI_CALENDAR} <b>Остання відмітка:</b> <b>{last_date}</b>"
    )

    await update.message.reply_html(msg)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_user(user_id, last_date=None, streak=0)
    await update.message.reply_text("Серія скинута. Починай заново.")

async def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setprice", set_price))
    app.add_handler(CommandHandler("mark", mark))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reset", reset))
    print("Бот працює…")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
