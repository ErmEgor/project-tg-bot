import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
import aiohttp
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN", "7711881075:AAH9Yvz9vRTabNUcn7fk5asEX6RoL0Gy9_k")
ADMIN_ID = os.getenv("ADMIN_ID", "7586559527")
WEBAPP_URL = "https://project-tg-frontend-git-main-ermegors-projects.vercel.app/"
SERVER_URL = "https://project-tg-server.onrender.com/submit"

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def send_log_to_admin(message):
    await bot.send_message(chat_id=ADMIN_ID, text=f"Лог (main.py): {message}")

@dp.message(CommandStart())
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть портфолио", web_app=types.WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer("Привет! Это мой бот-портфолио. Нажми на кнопку, чтобы посмотреть мои проекты и оставить заявку!", reply_markup=keyboard)
    logger.info(f"Пользователь {message.from_user.id} запустил бота")
    await send_log_to_admin(f"Пользователь {message.from_user.id} запустил бота")

@dp.message()
async def handle_message(message: types.Message):
    if message.web_app_data:
        data = message.web_app_data.data
        logger.info(f"Получены данные из Web App от {message.from_user.id}: {data}")
        await send_log_to_admin(f"Получены данные из Web App от {message.from_user.id}: {data}")
        
        try:
            form_data = json.loads(data)
            name = form_data.get('name', 'Не указано')
            message_text = form_data.get('message', 'Не указано')
            
            msg = f"<b>Новая заявка (через Telegram)</b>\nИмя: {name}\nСообщение: {message_text}"
            await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="HTML")
            logger.info(f"Сообщение отправлено администратору: {msg}")
            await send_log_to_admin(f"Сообщение отправлено администратору: {msg}")
            
            # Перенаправляем данные на server.py
            async with aiohttp.ClientSession() as session:
                try:
                    logger.info(f"Перенаправляем данные на сервер: {data}")
                    await send_log_to_admin(f"Перенаправляем данные на сервер: {data}")
                    async with session.post(SERVER_URL, json=form_data) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Ошибка перенаправления на сервер: {error_text}")
                            await send_log_to_admin(f"Ошибка перенаправления на сервер: {error_text}")
                        else:
                            logger.info("Данные успешно перенаправлены на сервер")
                            await send_log_to_admin("Данные успешно перенаправлены на сервер")
                except Exception as e:
                    logger.error(f"Ошибка перенаправления: {str(e)}")
                    await send_log_to_admin(f"Ошибка перенаправления: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {str(e)}")
            await send_log_to_admin(f"Ошибка декодирования JSON: {str(e)}")
            await bot.send_message(chat_id=ADMIN_ID, text="Ошибка: Неверный формат данных из Web App")
    else:
        await message.answer("Пожалуйста, используй Web App для отправки заявки.")

async def on_startup():
    await send_log_to_admin("Бот запущен")
    logger.info("Бот запущен")

if __name__ == "__main__":
    logger.info("Запускаем бота...")
    dp.startup.register(on_startup)
    dp.run_polling(bot)