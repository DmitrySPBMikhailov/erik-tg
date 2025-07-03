from telebot import TeleBot, types
from dotenv import load_dotenv
import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("MY_JSON_KEY")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
# Авторизация в гугл
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)

# Открываем таблицу по id
SPREADSHEET_ID = os.getenv("MY_SPREAD_SHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

API_TOKEN = os.getenv("MY_API_KEY")
bot = TeleBot(API_TOKEN)

# Словарь для хранения данных по пользователю
user_data = {}


# доп функция для сбора данных. Используется ниже
def ask_contact(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_button = types.KeyboardButton(
        "Отправить номер телефона", request_contact=True
    )
    markup.add(contact_button)
    bot.send_message(
        message.chat.id,
        "Пожалуйста, отправьте номер телефона, нажав кнопку ниже.",
        reply_markup=markup,
    )


# старт
@bot.message_handler(commands=["start"])
def main(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🪪 Активировать Amora Pass"))
    bot.send_message(
        message.chat.id,
        "Добро пожаловать! Нажмите кнопку ниже для активации:",
        reply_markup=markup,
    )


@bot.message_handler(func=lambda message: message.text == "🪪 Активировать Amora Pass")
def ask_consent(message):
    user_data[message.from_user.id] = {"step": "awaiting_consent"}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✅ Согласен"))
    bot.send_message(
        message.chat.id,
        "При активации Amora Pass вы даёте согласие на обработку персональных данных.",
        reply_markup=markup,
    )


@bot.message_handler(func=lambda message: message.text == "✅ Согласен")
def ask_code(message):
    uid = message.from_user.id
    if uid in user_data and user_data[uid].get("step") == "awaiting_consent":
        user_data[uid]["step"] = "awaiting_code"
        bot.send_message(message.chat.id, "Пожалуйста, введите ваш код:")


# обработка инпута от пользователя
@bot.message_handler(func=lambda message: message.content_type == "text")
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id not in user_data:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, нажмите кнопку «Активировать Amora Pass» для начала.",
        )
        return

    step = user_data[user_id].get("step")

    if step == "awaiting_code":
        try:
            codes_range = worksheet.range("A2:A20")
            found = None
            for cell in codes_range:
                if cell.value == text:
                    found = cell.row
                    break
            if found:
                activation_value = worksheet.cell(found, 6).value  # колонка F
                if activation_value:
                    bot.send_message(message.chat.id, "⛔ Этот код уже активирован.")
                    return
                # Код принят
                user_data[user_id].update({"row": found, "code": text, "step": "vk_id"})
                bot.send_message(message.chat.id, "Код принят. Введите ваш VK ID:")
            else:
                bot.send_message(message.chat.id, "Код не найден. Попробуйте ещё раз.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при поиске кода: {str(e)}")

    elif step == "vk_id":
        user_data[user_id]["vk_id"] = text
        user_data[user_id]["step"] = "email"
        bot.send_message(message.chat.id, "Введите ваш email:")

    elif step == "email":
        user_data[user_id]["email"] = text
        full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        if full_name:
            user_data[user_id]["name"] = full_name
            user_data[user_id]["step"] = "confirm"
            ask_contact(message)
        else:
            user_data[user_id]["step"] = "name"
            bot.send_message(message.chat.id, "Введите ваше имя полностью:")

    elif step == "name":
        user_data[user_id]["name"] = text
        user_data[user_id]["step"] = "confirm"
        ask_contact(message)


@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    user_id = message.from_user.id
    if user_id in user_data and user_data[user_id].get("step") == "confirm":
        try:
            row = user_data[user_id]["row"]
            telegram_id = str(user_id)
            vk_id = user_data[user_id]["vk_id"]
            name = user_data[user_id]["name"]
            email = user_data[user_id]["email"]
            phone = message.contact.phone_number
            activation_date = datetime.now().strftime("%Y-%m-%d %H:%M")

            worksheet.update_acell(f"B{row}", telegram_id)
            worksheet.update_acell(f"C{row}", vk_id)
            worksheet.update_acell(f"D{row}", name)
            worksheet.update_acell(f"E{row}", email)
            worksheet.update_acell(f"F{row}", activation_date)

            bot.send_message(message.chat.id, "✅ Спасибо! Активация прошла успешно.")
            user_data.pop(user_id)

        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при записи в таблицу: {str(e)}")
    else:
        bot.send_message(message.chat.id, "Сначала активируйте Amora Pass.")


bot.infinity_polling()
