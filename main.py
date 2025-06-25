from telebot import TeleBot, types
from dotenv import load_dotenv
import os

load_dotenv()
API_TOKEN = os.getenv("MY_API_KEY")

bot = TeleBot(API_TOKEN)


@bot.message_handler(commands=["start"])
def main(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_button = types.KeyboardButton(
        "Отправить номер телефона", request_contact=True
    )
    markup.add(contact_button)
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name} {message.from_user.last_name}! Ваш ник @{message.from_user.username} \nПожалуйста, отправьте свой номер телефона:",
        reply_markup=markup,
    )


# Обработка контакта
@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    if message.contact is not None:
        phone = message.contact.phone_number
        bot.send_message(message.chat.id, f"Спасибо!! Вы прислали номер: {phone}")


# Обработка остальных сообщений
@bot.message_handler(func=lambda message: True)
def info(message):
    bot.reply_to(message, f"Ты ввел: {message.text}")


bot.infinity_polling()
