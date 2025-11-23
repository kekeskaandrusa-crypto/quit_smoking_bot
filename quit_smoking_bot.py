Андрей, [23.11.2025 14:55]
# quit_smoking_bot.py — финальная версия для Render / Railway / любого хостинга
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.request import HTTPXRequest
import sqlite3
import os

# ТОКЕН БЕРЁТСЯ ИЗ ПЕРЕМЕННОЙ ОКРУЖЕНИЯ (для безопасности на хостинге)
TOKEN = os.getenv("TOKEN", "8494695438:AAGhWgVDDfXf3eRkxpbOcyYd9Yc956ZPgcU")

QUIT_DATE, CIGS_PER_DAY, PRICE_PER_PACK, PACK_SIZE = range(4)
logging.basicConfig(level=logging.INFO)

# База данных
def init_db():
    conn = sqlite3.connect('quit_smoking.db')
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
    conn = sqlite3.connect('quit_smoking.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def save_user(user_id, quit_date, cigs, price, pack):
    conn = sqlite3.connect('quit_smoking.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)",
              (user_id, quit_date, cigs, price, pack))
    conn.commit()
    conn.close()

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_user(user_id):
        await show_stats(update, context)
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("Я бросил курить!", callback_data="setup")]]
    await update.message.reply_text(
        "Привет! Я — бот, который поможет тебе бросить курить навсегда 🔥\n\n"
        "Я буду считать:\n"
        "• Сколько сигарет ты НЕ выкурил\n"
        "• Сколько евро сэкономил\n"
        "• Сколько жизни вернул себе\n\n"
        "Нажми кнопку ниже →",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return QUIT_DATE

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "setup":
        await query.edit_message_text("Когда ты бросил курить?\nНапиши дату ДД.ММ.ГГГГ или «сегодня»")
        return QUIT_DATE
    if query.data == "stats":
        await show_stats(update, context)

async def quit_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text == "сегодня":
        date = datetime.now().strftime("%d.%m.%Y")
    else:
        try:
            date = datetime.strptime(text, "%d.%m.%Y").strftime("%d.%m.%Y")
        except:
            await update.message.reply_text("Неправильный формат. Пример: 23.11.2025 или «сегодня»")
            return QUIT_DATE
    context.user_data["quit_date"] = date
    await update.message.reply_text("Сколько сигарет в день ты курил в среднем?")
    return CIGS_PER_DAY

async def cigs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(update.message.text)
        if not 1 <= n <= 200: raise ValueError
        context.user_data["cigs"] = n
        await update.message.reply_text("Сколько стоит одна пачка в евро? (например 7.50)")
        return PRICE_PER_PACK
    except:
        await update.message.reply_text("Напиши число (например 20)")
        return CIGS_PER_DAY

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        p = float(update.message.text.replace(",", "."))
        if p <= 0: raise ValueError
        context.user_data["price"] = p
        await update.message.reply_text("Сколько сигарет в пачке? (обычно 20)")
        return PACK_SIZE
    except:
        await update.message.reply_text("Напиши цену правильно (например 7.80)")
        return PRICE_PER_PACK

Андрей, [23.11.2025 14:55]
async def pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ps = int(update.message.text)
        if ps < 1: raise ValueError
        user_id = update.effective_user.id
        save_user(user_id,
                  context.user_data["quit_date"],
                  context.user_data["cigs"],
                  context.user_data["price"],
                  ps)
        await update.message.reply_text("Всё сохранено! Теперь в любой момент жми кнопку ниже или пиши /stats")
        await show_stats(update, context)
        return ConversationHandler.END
    except:
        await update.message.reply_text("Напиши число (например 20)")
        return PACK_SIZE

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    data = get_user(user_id)
    if not data:
        text = "Сначала настрой бота — нажми /start"
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    quit_date_str, cigs_day, price_pack, pack_size = data[1], data[2], data[3], data[4]
    quit_date = datetime.strptime(quit_date_str, "%d.%m.%Y").date()
    days = (datetime.now().date() - quit_date).days + 1

    saved_cigs = cigs_day * days
    saved_packs = saved_cigs / pack_size
    saved_money = saved_packs * price_pack
    saved_minutes = saved_cigs * 11
    saved_days_life = saved_minutes // (24 * 60)
    saved_hours_life = (saved_minutes % (24 * 60)) // 60

    text = f"""
Твоя победа над сигаретами 💪

Бросил: <b>{quit_date_str}</b>
Дней без сигарет: <b>{days}</b>

НЕ выкурено: <b>{saved_cigs:,}</b> сигарет
Сэкономлено пачек: <b>{saved_packs:.1f}</b>

Вернул жизни: <b>{saved_days_life} дн. {saved_hours_life} ч.</b>

СЭКОНОМИЛ: <b>{saved_money:.2f} €</b>

Ты — легенда! Продолжай 🔥
    """.strip()

    keyboard = [
        [InlineKeyboardButton("Обновить статистику", callback_data="stats")],
        [InlineKeyboardButton("Сбросить всё", callback_data="reset")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect('quit_smoking.db')
    conn.execute("DELETE FROM users WHERE user_id = ?", (query.from_user.id,))
    conn.commit()
    conn.close()
    await query.edit_message_text("Данные сброшены! Нажми /start и начни заново")

# ЗАПУСК
def main():
    init_db()

    # Защита от блокировок и таймаутов
    request = HTTPXRequest(connect_timeout=60, read_timeout=60, pool_timeout=90)
    app = Application.builder().token(TOKEN).request(request).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, quit_date)],
            CIGS_PER_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, cigs)],
            PRICE_PER_PACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
            PACK_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pack)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CallbackQueryHandler(button, pattern="^(setup|stats)$"))
    app.add_handler(CallbackQueryHandler(reset, pattern="^reset$"))

    print("БОТ УСПЕШНО ЗАПУЩЕН! ОН РАБОТАЕТ 24/7")
    app.run_polling(drop_pending_updates=True)

if name == "__main__":
    main()
