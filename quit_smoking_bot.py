import os
import logging
from datetime import datetime

import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

TOKEN = os.getenv("TOKEN", "8494695438:AAGhWgVDDfXf3eRkxpbOcyYd9Yc956ZPgcU")

# Состояния разговора
(QUIT_DATE, CIGS_PER_DAY, PRICE_PER_PACK, PACK_SIZE) = range(4)

logging.basicConfig(level=logging.INFO)

# === БАЗА ДАННЫХ ===
def init_db():
    conn = sqlite3.connect("quit_smoking.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    quit_date TEXT,
                    cigs_per_day INTEGER,
                    price_per_pack REAL,
                    pack_size INTEGER)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("quit_smoking.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def save_user(user_id, quit_date, cigs, price, pack):
    conn = sqlite3.connect("quit_smoking.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)",
              (user_id, quit_date, cigs, price, pack))
    conn.commit()
    conn.close()

# === КОМАНДЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_user(user_id):
        await show_stats(update, context)
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("Я бросил курить!", callback_data="setup")]]
    await update.message.reply_text(
        "Привет! Я помогу тебе бросить курить навсегда\n\n"
        "Я посчитаю:\n"
        "• Сколько дней ты уже не куришь\n"
        "• Сколько сигарет НЕ выкурил\n"
        "• Сколько денег сэкономил\n\n"
        "Нажми кнопку →",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return QUIT_DATE

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "setup":
        await query.edit_message_text("Когда ты бросил курить?\nНапиши: сегодня или дату ДД.ММ.ГГГГ")
        return QUIT_DATE
    if query.data == "stats":
        await show_stats(update, context)

# Ввод даты
async def quit_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "сегодня":
        date = datetime.now().strftime("%d.%m.%Y")
    else:
        try:
            date = datetime.strptime(text, "%d.%m.%Y").strftime("%d.%m.%Y")
        except:
            await update.message.reply_text("Неправильно Напиши: сегодня или 23.11.2025")
            return QUIT_DATE
    context.user_data["quit_date"] = date
    await update.message.reply_text("Сколько сигарет в день ты курил?")
    return CIGS_PER_DAY

# Ввод сигарет в день
async def cigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(update.message.text)
        if 1 <= n <= 200:
            context.user_data["cigs"] = n
            await update.message.reply_text("Сколько стоит пачка сигарет в евро? (например 7.50)")
            return PRICE_PER_PACK
        else:
            raise ValueError
    except:
        await update.message.reply_text("Напиши число от 1 до 200")
        return CIGS_PER_DAY

# Ввод цены пачки
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        p = float(update.message.text.replace(",", "."))
        if p > 0:
            context.user_data["price"] = p
            await update.message.reply_text("Сколько сигарет в пачке? (обычно 20)")
            return PACK_SIZE
        else:
            raise ValueError
    except:
        await update.message.reply_text("Напиши цену правильно (например 7.50)")
        return PRICE_PER_PACK

# Ввод размера пачки + сохранение
async def pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ps = int(update.message.text)
        if ps >= 1:
            user_id = update.effective_user.id
            save_user(user_id,
                      context.user_data["quit_date"],
                      context.user_data["cigs"],
                      context.user_data["price"],
                      ps)
            await update.message.reply_text("Готово! Теперь пиши /stats в любой момент")
            await show_stats(update, context)
            return ConversationHandler.END
    except:
        await update.message.reply_text("Напиши число (например 20)")
        return PACK_SIZE

# === СТАТИСТИКА ===
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.callback_query:
        user_id = update.callback_query.from_user.id

    data = get_user(user_id)
    if not data:
        text = "Ты ещё не настроил бота\nНажми /start"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    quit_date_str, cigs_per_day, price_per_pack, pack_size = data[1], data[2], data[3], data[4]
    quit_date = datetime.strptime(quit_date_str, "%d.%m.%Y").date()
    days = (datetime.now().date() - quit_date).days + 1

    not_smoked = cigs_per_day * days
    saved_money = (not_smoked / pack_size) * price_per_pack

    text = f"""Твоя статистика бросания курить

Бросил: <b>{quit_date_str}</b>
Дней без сигарет: <b>{days}</b>

НЕ выкурил: <b>{not_smoked:,}</b> сигарет
Сэкономил: <b>{saved_money:.2f} €</b>

Ты молодец! Продолжай!"""

    keyboard = [
        [InlineKeyboardButton("Обновить статистику", callback_data="stats")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML"
        )

# === ЗАПУСК (работает на Render, Railway, Fly.io) ===
async def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, quit_date)],
            CIGS_PER_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, cigs)],
            PRICE_PER_PACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
            PACK_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pack)],
        },
        fallbacks=[],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CallbackQueryHandler(button, pattern="^(setup|stats)$"))

    # Для Render / Railway — webhook
    port = int(os.environ.get("PORT", 10000))
    await app.initialize()
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME') or os.environ.get('RAILWAY_STATIC_URL') or 'your-app.onrender.com'}/{TOKEN}"
    )
    logging.info("Бот запущен через webhook!")
    await app.updater.bot.set_webhook(
        url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME') or os.environ.get('RAILWAY_STATIC_URL') or 'your-app.onrender.com'}/{TOKEN}"
    )

    # Держим бота живым
    import asyncio
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
