import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import random
import time
import threading
import re
from datetime import datetime

# ========== ВАШИ ДАННЫЕ ==========
BOT_TOKEN = "8846825715:AAFiEmV3oMgNaOw6K98veE8QFZR70oXpynU"
OWNER_ID = 8281259050
CARD_NUMBER = "2200700916294340"   # карта Т-банка
# =================================

bot = telebot.TeleBot(BOT_TOKEN)

# База данных для хранения заказов
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  order_type TEXT,
                  status TEXT,
                  reading TEXT,
                  created_at TIMESTAMP)''')
    conn.commit()
    conn.close()
init_db()

# Генерация расклада через GPT (бесплатный g4f)
def get_gpt_reading(prompt_type):
    # Подготавливаем запрос в зависимости от типа
    prompts = {
        "love": "Сделай расклад Таро на любовные отношения. Напиши 5-7 предложений. Будь конкретен.",
        "money": "Сделай расклад Таро на финансовое благополучие и карьеру. Напиши 5-7 предложений.",
        "future": "Сделай общий расклад Таро на ближайшее будущее. Напиши 5-7 предложений.",
        "health": "Сделай расклад Таро на здоровье. Напиши 5-7 предложений."
    }
    query = prompts.get(prompt_type, prompts["future"])
    try:
        import g4f
        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": query}],
        )
        return response
    except Exception as e:
        # Запасной вариант
        return f"✨ Карты говорят: {random.choice(['удача', 'перемены', 'встреча'])} ждёт вас. (GPT временно недоступен, ошибка: {e})"

# Клавиатура выбора расклада
def get_choice_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(KeyboardButton("💖 Любовь и отношения"), 
               KeyboardButton("💰 Финансы и карьера"),
               KeyboardButton("🔮 Общее будущее"),
               KeyboardButton("🌿 Здоровье"))
    return markup

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    bot.send_message(user_id,
                     f"✨ Привет! Я нейросетевой таролог. Выбери тип расклада:",
                     reply_markup=get_choice_keyboard())

# Обработка выбора расклада
@bot.message_handler(func=lambda m: m.text in ["💖 Любовь и отношения", "💰 Финансы и карьера", "🔮 Общее будущее", "🌿 Здоровье"])
def handle_choice(message):
    user_id = message.from_user.id
    choice_map = {
        "💖 Любовь и отношения": "love",
        "💰 Финансы и карьера": "money",
        "🔮 Общее будущее": "future",
        "🌿 Здоровье": "health"
    }
    order_type = choice_map[message.text]
    
    # Сохраняем заказ в БД со статусом "waiting_payment"
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, order_type, status, created_at) VALUES (?,?,?,?)",
              (user_id, order_type, "waiting_payment", datetime.now().isoformat()))
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    
    bot.send_message(user_id,
                     f"🔮 Ты выбрал расклад: {message.text}\n\n"
                     f"💳 Стоимость: 199 руб.\n"
                     f"Переведи на карту Т-банка:\n`{CARD_NUMBER}`\n"
                     f"В комментарии к переводу укажи:\n`Расклад {order_id}`\n\n"
                     f"После перевода нажми кнопку «Я перевел(а)» и напиши слово ПОДТВЕРЖДАЮ.\n"
                     f"Я отправлю расклад, как только получу подтверждение.\n\n"
                     f"⚠️ Важно: без комментария я не смогу связать платёж с заказом.",
                     parse_mode="Markdown",
                     reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Я перевел(а)", callback_data=f"paid_{order_id}")))

# Колбэк для кнопки "Я перевел(а)"
@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def paid_callback(call):
    user_id = call.from_user.id
    order_id = int(call.data.split("_")[1])
    bot.send_message(user_id,
                     "Ожидаю подтверждения. Напишите в этот чат слово **ПОДТВЕРЖДАЮ** (заглавными буквами).\n"
                     "После этого я сразу пришлю расклад.",
                     parse_mode="Markdown")
    # Можно сохранить состояние, но для простоты используем ожидание текста

# Обработка команды ПОДТВЕРЖДАЮ
@bot.message_handler(func=lambda m: m.text and m.text.upper() == "ПОДТВЕРЖДАЮ")
def confirm_payment(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    # Находим последний незавершённый заказ пользователя
    c.execute("SELECT id, order_type FROM orders WHERE user_id=? AND status='waiting_payment' ORDER BY created_at DESC LIMIT 1", (user_id,))
    row = c.fetchone()
    if not row:
        bot.send_message(user_id, "❌ Нет активных заказов. Начни заново через /start")
        conn.close()
        return
    order_id, order_type = row
    
    # Генерируем расклад через GPT
    reading = get_gpt_reading(order_type)
    
    # Обновляем заказ
    c.execute("UPDATE orders SET status='completed', reading=? WHERE id=?", (reading, order_id))
    conn.commit()
    conn.close()
    
    # Отправляем расклад пользователю
    bot.send_message(user_id, f"🔮 Твой расклад готов:\n\n{reading}")
    
    # Уведомляем владельца
    bot.send_message(OWNER_ID,
                     f"💰 Пользователь {user_id} подтвердил оплату заказа №{order_id}.\n"
                     f"Проверь перевод на карту {CARD_NUMBER} на сумму 199 руб с комментарием 'Расклад {order_id}'. Если денег нет — заблокируй пользователя.")

# Команда /report для владельца
@bot.message_handler(commands=['report'])
def report(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.from_user.id, "Доступ запрещён.")
        return
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders WHERE status='completed'")
    completed = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM orders WHERE status='waiting_payment'")
    waiting = c.fetchone()[0]
    total_money = completed * 199
    bot.send_message(OWNER_ID,
                     f"📊 Отчёт по заказам:\n✅ Выполнено: {completed}\n⏳ Ожидают оплаты: {waiting}\n💰 Выручка: {total_money} руб.")
    conn.close()

# Команда /cancel для отмены текущего заказа
@bot.message_handler(commands=['cancel'])
def cancel(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("UPDATE orders SET status='cancelled' WHERE user_id=? AND status='waiting_payment'", (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(user_id, "Текущий заказ отменён. Можешь начать заново /start")

# Запуск бота
print("✅ Бот запущен. Ожидание сообщений...")
bot.infinity_polling()
