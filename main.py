import telebot

# ===== ВАШИ ДАННЫЕ (вписаны напрямую) =====
BOT_TOKEN = "8846825715:AAFiEmV3oMgNaOw6K98veE8QFZR70oXpynU"
OWNER_ID = 8281259050
YOOMONEY_WALLET = "4100119544367845"
# =========================================

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    bot.send_message(user_id,
                     f"✨ Привет! Полный расклад Таро — 199 руб.\n\n"
                     f"Переведите на кошелёк ЮMoney: `{YOOMONEY_WALLET}`\n"
                     f"В комментарии **обязательно** укажите ваш Telegram ID: `{user_id}`\n\n"
                     f"После перевода **напишите сюда слово ПОДТВЕРЖДАЮ** — я пришлю расклад.\n"
                     f"Спасибо за доверие! 🔮",
                     parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.upper() == "ПОДТВЕРЖДАЮ")
def confirm(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "🔮 Ваш расклад: Вас ждёт удача в финансах. Будьте внимательны к новым возможностям!")
    bot.send_message(OWNER_ID, f"💰 Пользователь {user_id} подтвердил платёж (нужно проверить в банке).")

print("✅ Бот успешно запущен и работает!")
bot.infinity_polling()
