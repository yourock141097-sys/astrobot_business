import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import random
import time
import threading
import re
from datetime import datetime

# ========== ДАННЫЕ (уже ваши) ==========
BOT_TOKEN = "8846825715:AAFiEmV3oMgNaOw6K98veE8QFZR70oXpynU"
OWNER_ID = 8281259050
CARD_NUMBER = "2200700916294340"
# =======================================

bot = telebot.TeleBot(BOT_TOKEN)
bot.send_chat_action = lambda chat_id, action: telebot.types.ChatAction.typing

# Хранилище заказов
orders = {}
order_counter = 1

# ========== Функция GPT через g4f ==========
def get_gpt_reading(prompt_type):
    prompts = {
        "love": "Ты опытный таролог. Сделай расклад Таро на любовь и отношения. Напиши 5-7 предложений тёплым, загадочным тоном. Будь конкретен, добавь совет.",
        "money": "Ты таролог. Сделай расклад Таро на финансовое благополучие и карьеру. 5-7 предложений, вдохновляющий, с практическим советом.",
        "future": "Сделай общий расклад Таро на ближайшее будущее (месяц). 5-7 предложений, таинственно и обнадёживающе.",
        "health": "Сделай расклад Таро на здоровье и энергию. 5-7 предложений, мягко, без страшилок, дай рекомендации."
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
        # Запасной вариант на случай сбоя g4f
        fallback = {
            "love": "✨ Карты говорят: скоро в вашу жизнь войдёт человек, который изменит многое. Будьте открыты, но не теряйте себя.",
            "money": "💰 Финансовая удача повернётся к вам, когда вы завершите старые дела. Обратите внимание на долги.",
            "future": "🔮 В ближайшие недели произойдёт событие, которое заставит улыбнуться. Доверьтесь потоку.",
            "health": "🌿 Ваша энергия восстанавливается. Дайте себе отдых и не забывайте дышать."
        }
        return fallback.get(prompt_type, fallback["future"]) + f" (Ошибка GPT: {e})"

# ========== Клавиатуры ==========
def get_choice_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(KeyboardButton("💖 Любовь и отношения"), KeyboardButton("💰 Финансы и карьера"))
    markup.add(KeyboardButton("🔮 Общее будущее"), KeyboardButton("🌿 Здоровье"))
    markup.add(KeyboardButton("🎲 Случайный расклад"))
    return markup

def after_payment_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Я перевёл(а)", callback_data="i_paid"))
    return markup

# ========== Команда /start ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    welcome_text = (
        f"✨ *Здравствуйте, {name}!* ✨\n\n"
        f"Я — *AI Таролог*, нейросеть, обученная на тысячах раскладов.\n"
        f"Я не человек, но чувствую энергию чисел и звёзд.\n\n"
        f"Выберите тему, которая вас волнует, и я сделаю *точный расклад*.\n"
        f"Стоимость — всего *199 рублей* за полный прогноз от GPT.\n\n"
        f"👇 *Нажмите на кнопку ниже*"
    )
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1)
    bot.send_message(user_id, welcome_text, parse_mode="Markdown", reply_markup=get_choice_keyboard())

# ========== Обработка выбора темы ==========
@bot.message_handler(func=lambda m: m.text in ["💖 Любовь и отношения", "💰 Финансы и карьера", "🔮 Общее будущее", "🌿 Здоровье", "🎲 Случайный расклад"])
def handle_choice(message):
    global order_counter
    user_id = message.from_user.id
    name = message.from_user.first_name
    choice_map = {
        "💖 Любовь и отношения": "love",
        "💰 Финансы и карьера": "money",
        "🔮 Общее будущее": "future",
        "🌿 Здоровье": "health",
        "🎲 Случайный расклад": random.choice(["love", "money", "future", "health"])
    }
    order_type = choice_map[message.text]
    order_id = order_counter
    order_counter += 1
    orders[user_id] = {"type": order_type, "order_id": order_id, "status": "waiting"}
    
    bot.send_chat_action(user_id, 'typing')
    time.sleep(1.5)
    
    bot.send_message(user_id,
                     f"🔮 *{name}*, хороший выбор.\n"
                     f"Я уже чувствую вибрации...\n\n"
                     f"💰 *Стоимость расклада:* 199 ₽\n"
                     f"💳 *Карта для перевода:* `{CARD_NUMBER}`\n"
                     f"📝 *Обязательный комментарий:* `Расклад {order_id}`\n\n"
                     f"После перевода нажмите кнопку и напишите слово *ПОДТВЕРЖДАЮ*.\n"
                     f"Я сразу же отправлю ваш персональный прогноз.\n\n"
                     f"*Важно:* без комментария я не смогу вас узнать, и расклад не дойдёт.",
                     parse_mode="Markdown",
                     reply_markup=after_payment_keyboard())

# ========== Кнопка "Я перевёл" ==========
@bot.callback_query_handler(func=lambda call: call.data == "i_paid")
def paid_callback(call):
    user_id = call.from_user.id
    name = call.from_user.first_name
    bot.answer_callback_query(call.id)
    bot.send_message(user_id,
                     f"✨ Отлично, *{name}*! Я жду подтверждения.\n"
                     f"Просто напишите в этот чат слово *ПОДТВЕРЖДАЮ* (заглавными буквами).\n"
                     f"Как только проверю перевод, расклад придёт сюда.",
                     parse_mode="Markdown")

# ========== Подтверждение оплаты ==========
@bot.message_handler(func=lambda m: m.text and m.text.upper() == "ПОДТВЕРЖДАЮ")
def confirm_payment(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    if user_id not in orders or orders[user_id]["status"] != "waiting":
        bot.send_message(user_id, "❌ У вас нет активного заказа. Начните с /start")
        return
    
    order = orders[user_id]
    order_id = order["order_id"]
    order_type = order["type"]
    
    # Эффект "думает"
    bot.send_chat_action(user_id, 'typing')
    thinking_msg = bot.send_message(user_id, "🔮 Раскладываю карты... Медитирую... ⏳")
    time.sleep(3)
    bot.delete_message(user_id, thinking_msg.message_id)
    
    # Генерируем расклад через GPT
    reading = get_gpt_reading(order_type)
    
    # Отправляем расклад
    bot.send_chat_action(user_id, 'typing')
    reading_text = f"🔮 *Ваш персональный расклад Таро, {name}:*\n\n{reading}\n\n✨ *Благодарю за доверие!* ✨"
    bot.send_message(user_id, reading_text, parse_mode="Markdown")
    
    # Отмечаем заказ выполненным
    orders[user_id]["status"] = "completed"
    
    # Уведомление владельцу
    bot.send_message(OWNER_ID,
                     f"💰 *Пользователь {name} (ID {user_id})* подтвердил оплату заказа №{order_id}.\n"
                     f"Проверьте карту {CARD_NUMBER}: перевод 199 ₽ с комментарием 'Расклад {order_id}'.\n"
                     f"Если перевода нет — заблокируйте пользователя.")
    
    # Просим обратную связь
    time.sleep(2)
    feedback_markup = InlineKeyboardMarkup()
    feedback_markup.add(InlineKeyboardButton("👍 Да, помог", callback_data="feedback_yes"),
                        InlineKeyboardButton("👎 Нет, не помог", callback_data="feedback_no"))
    bot.send_message(user_id,
                     "🙏 Мне важно ваше мнение. Расклад оказался полезным?",
                     reply_markup=feedback_markup)

# ========== Обратная связь ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith("feedback_"))
def feedback(call):
    user_id = call.from_user.id
    if call.data == "feedback_yes":
        bot.answer_callback_query(call.id, "Спасибо! Рад помочь ✨")
        bot.send_message(user_id, "✨ Пусть звёзды вам улыбаются!")
    else:
        bot.answer_callback_query(call.id, "Жаль. Постараюсь стать лучше 🌙")
        bot.send_message(user_id, "🌙 Спасибо за честность. Я учусь на каждом отзыве.")
    # Можно сохранять отзывы в базу, но для простоты просто ответим

# ========== Команды для владельца ==========
@bot.message_handler(commands=['report'])
def report(message):
    if message.from_user.id != OWNER_ID:
        return
    completed = sum(1 for o in orders.values() if o["status"] == "completed")
    waiting = sum(1 for o in orders.values() if o["status"] == "waiting")
    bot.send_message(OWNER_ID, f"📊 *Статистика*\n✅ Выполнено: {completed}\n⏳ Ожидают: {waiting}\n💰 Выручка: {completed*199} ₽", parse_mode="Markdown")

@bot.message_handler(commands=['check'])
def check(message):
    if message.from_user.id != OWNER_ID:
        return
    waiting_list = [f"• {uid} — заказ №{o['order_id']}, тема {o['type']}" for uid, o in orders.items() if o["status"] == "waiting"]
    if waiting_list:
        bot.send_message(OWNER_ID, "⏳ *Ожидают подтверждения:*\n" + "\n".join(waiting_list), parse_mode="Markdown")
    else:
        bot.send_message(OWNER_ID, "Нет ожидающих заказов.")

# ========== Запуск ==========
print("✨ Бот-таролог запущен и ждёт клиентов ✨")
bot.infinity_polling()
