from telebot import TeleBot, types
from dotenv import load_dotenv
import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("MY_JSON_KEY")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = os.getenv("MY_SPREAD_SHEET_ID")
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

API_TOKEN = os.getenv("MY_API_KEY")
bot = TeleBot(API_TOKEN)

# Храним шаги пользователей
user_data = {}

# список админов
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))


# старт
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "✨ Пожалуйста, введите ваш код:")


# обработка ввода кода
@bot.message_handler(
    func=lambda message: message.text and not message.text.startswith("/")
)
def handle_code(message):
    user_id = message.from_user.id
    text = message.text.strip()

    bot.send_message(message.chat.id, "🔎 Поиск...")  # <-- промежуточный ответ

    try:
        codes_range = worksheet.range("A2:A501")  # список кодов в колонке A
        found = None
        for cell in codes_range:
            if cell.value == text:
                found = cell.row
                break

        if found:
            tg_id_cell = worksheet.cell(found, 2).value  # колонка B
            if tg_id_cell:  # уже записан ID
                bot.send_message(message.chat.id, "⛔ Этот код уже активирован.")
                return

            # записываем только Telegram ID
            worksheet.update_acell(f"B{found}", str(user_id))
            worksheet.update_acell(
                f"C{found}", datetime.now().strftime("%Y-%m-%d %H:%M")
            )  # опционально время
            bot.send_message(
                message.chat.id,
                "✅ Всё получилось. С этого момента мы вместе, и Amora Pass будет открывать "
                "для тебя всё больше привилегий с партнёрами Amora.",
            )

        else:
            bot.send_message(
                message.chat.id,
                "❌ Дорогое сердце, проверь пожалуйста код ещё раз. "
                "К сожалению, я не нашёл такого в моей базе.",
            )

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при поиске кода: {str(e)}")


# команда для запуска рассылки
@bot.message_handler(commands=["broadcast"])
def start_broadcast(message):
    if message.from_user.id not in ADMINS:
        bot.reply_to(message, "⛔ У вас нет прав для этой команды.")
        return

    bot.send_message(message.chat.id, "✍️ Введите текст рассылки одним сообщением:")
    bot.register_next_step_handler(message, process_broadcast)


def process_broadcast(message):
    if message.from_user.id not in ADMINS:
        return

    text = message.text
    bot.send_message(message.chat.id, f"📢 Начинаю рассылку...\n\nТекст:\n{text}")

    try:
        tg_ids = worksheet.col_values(2)[1:]  # колонка B (Telegram ID), без заголовка
        sent, failed = 0, 0
        for tg_id in tg_ids:
            if tg_id.strip():
                try:
                    bot.send_message(int(tg_id), text)
                    sent += 1
                except Exception as e:
                    print(f"Ошибка при отправке {tg_id}: {e}")
                    failed += 1

        bot.send_message(
            message.chat.id,
            f"✅ Рассылка завершена.\nУспешно: {sent}\nОшибок: {failed}",
        )

    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при рассылке: {str(e)}")


bot.infinity_polling()
