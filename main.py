import os
import telebot

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))
YOOMONEY_WALLET = os.environ.get("YOOMONEY_WALLET")

if not BOT_TOKEN or not OWNER_ID or not YOOMONEY_WALLET:
    print("Ошибка: не заданы BOT_TOKEN, OWNER_ID или YOOMONEY_WALLET")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    bot.send_message(user_id,
                     f"✨ Привет! Полный расклад Таро — 199 руб.\n\n"
                     f"Переведите на кошелёк ЮMoney: `{YOOMONEY_WALLET}`\n"
                     f"В комментарии **обязательно** укажите ваш Telegram ID: `{user_id}`\n\n"
                     f"После перевода **напишите сюда слово ПОДТВЕРЖДАЮ** — я пришлю расклад вручную (в течение часа).\n"
                     f"Спасибо за доверие! 🔮",
                     parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.upper() == "ПОДТВЕРЖДАЮ")
def confirm(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "🔮 Ваш расклад: Вас ждёт удача в финансах. Будьте внимательны к новым возможностям!")
    bot.send_message(OWNER_ID, f"💰 Пользователь {user_id} подтвердил платёж (нужно проверить в банке).")

print("Бот запущен (упрощённая версия)")
bot.infinity_polling()
