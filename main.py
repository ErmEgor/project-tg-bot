import asyncio
import json
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BotCommand
)
from aiohttp import web
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN", "7711881075:AAH9Yvz9vRTabNUcn7fk5asEX6RoL0Gy9_k")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7586559527"))
WEBHOOK_HOST = "https://project-tg-bot.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# CORS настройки
ALLOWED_ORIGINS = [
    "https://project-tg-frontend-git-main-ermegors-projects.vercel.app",
    "http://localhost:3000"
]

async def cors_middleware(app, handler):
    async def middleware(request):
        origin = request.headers.get('Origin', '')
        logger.info(f"[Middleware] Origin: {origin}, Method: {request.method}")
        await send_log_to_telegram(f"[Middleware] Origin: {origin}, Method: {request.method}")
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response
    return middleware

# Функция для отправки логов в Telegram
async def send_log_to_telegram(message):
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=f"<b>Лог (main.py):</b>\n{message}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Ошибка отправки лога в Telegram: {e}")

# --- Клавиатуры ---
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Помощь"), KeyboardButton(text="📱 Портфолио")],
        [KeyboardButton(text="ℹ️ Обо мне"), KeyboardButton(text="📩 Связаться")]
    ],
    resize_keyboard=True
)

portfolio_inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="📱 Приложение", web_app=types.WebAppInfo(url="https://project-tg-frontend-git-main-ermegors-projects.vercel.app/")),
        InlineKeyboardButton(text="🌐 Лендинг", url="https://ermegor.github.io/BuildMax/")
    ]
])

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Назад")]],
    resize_keyboard=True
)

help_keyboard = back_keyboard
about_keyboard = back_keyboard
contact_keyboard = back_keyboard

contact_inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="📧 Почта", url="mailto:ermilegor@gmail.com"),
        InlineKeyboardButton(text="📨 Telegram", url="tg://resolve?domain=prostof2p")
    ]
])

# --- Установка команд бота ---
async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Получить помощь"),
        BotCommand(command="portfolio", description="Посмотреть портфолио"),
        BotCommand(command="about", description="Узнать обо мне"),
        BotCommand(command="contact", description="Связаться со мной"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")
    await send_log_to_telegram("Команды бота установлены")

# --- Настройка вебхука ---
async def on_startup():
    logger.info("Проверяем и настраиваем вебхук...")
    await send_log_to_telegram("Проверяем и настраиваем вебхук...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Существующий вебхук удален")
        await send_log_to_telegram("Существующий вебхук удален")
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Текущее состояние вебхука: {webhook_info}")
        await send_log_to_telegram(f"Текущее состояние вебхука: {webhook_info}")
        if webhook_info.url:
            raise Exception("Вебхук не был удален!")
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука: {e}")
        await send_log_to_telegram(f"Ошибка при удалении вебхука: {e}")
        raise

    try:
        await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
        logger.info(f"Вебхук установлен на {WEBHOOK_URL}")
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Подтверждение установки вебхука: {webhook_info}")
        await send_log_to_telegram(f"Вебхук установлен: {webhook_info}")
        if webhook_info.url != WEBHOOK_URL:
            raise Exception("Вебхук не установлен корректно!")
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}")
        await send_log_to_telegram(f"Ошибка при установке вебхука: {e}")
        raise

async def on_shutdown():
    logger.info("Удаляем вебхук...")
    await send_log_to_telegram("Удаляем вебхук...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Вебхук удален")
        await send_log_to_telegram("Вебхук удален")
    except Exception as e:
        logger.error(f"Ошибка при удалении вебхука на завершении: {e}")
        await send_log_to_telegram(f"Ошибка при удалении вебхука: {e}")
    await bot.session.close()
    logger.info("Сессия бота закрыта")
    await send_log_to_telegram("Сессия бота закрыта")

# --- Обработчики Telegram ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    logger.info(f"Получена команда /start от {message.from_user.id}")
    await send_log_to_telegram(f"Команда /start от {message.from_user.id}")
    await message.answer(f"Здравствуй! Что тебя интересует?", reply_markup=main_keyboard)

@dp.message(Command("help"))
async def process_help_command(message: types.Message):
    logger.info(f"Получена команда /help от {message.from_user.id}")
    await send_log_to_telegram(f"Команда /help от {message.from_user.id}")
    await message.answer(
        "<b>Это раздел помощи.</b>\n"
        "Данный бот — одна из работ <b>Е.Егора</b>.\n"
        "Портфолио — список работ Егора.\n"
        "Приложение — мини-приложение внутри Telegram.\n"
        "Лендинг — полноценный сайт с работающими кнопками и дизайном.",
        parse_mode=ParseMode.HTML,
        reply_markup=help_keyboard
    )

@dp.message(lambda m: m.text == "📌 Помощь")
async def process_help_button(message: types.Message):
    logger.info(f"Нажата кнопка Помощь от {message.from_user.id}")
    await send_log_to_telegram(f"Нажата кнопка Помощь от {message.from_user.id}")
    await process_help_command(message)

@dp.message(Command("portfolio"))
async def process_portfolio_command(message: types.Message):
    logger.info(f"Получена команда /portfolio от {message.from_user.id}")
    await send_log_to_telegram(f"Команда /portfolio от {message.from_user.id}")
    await message.answer("Выбери проект:", reply_markup=portfolio_inline_keyboard)

@dp.message(lambda m: m.text == "📱 Портфолио")
async def process_portfolio_button(message: types.Message):
    logger.info(f"Нажата кнопка Портфолио от {message.from_user.id}")
    await send_log_to_telegram(f"Нажата кнопка Портфолио от {message.from_user.id}")
    await process_portfolio_command(message)

@dp.message(Command("about"))
async def process_about_command(message: types.Message):
    logger.info(f"Получена команда /about от {message.from_user.id}")
    await send_log_to_telegram(f"Команда /about от {message.from_user.id}")
    await message.answer(
        "<b>Обо мне</b>\n"
        "Меня зовут Егор, мне 14 лет. Я начинающий Telegram-разработчик.\n"
        "У меня есть проекты: сайт, бот и веб-приложение.\n"
        "Ищу заказы, чтобы расти и зарабатывать.",
        parse_mode=ParseMode.HTML,
        reply_markup=about_keyboard
    )

@dp.message(lambda m: m.text == "ℹ️ Обо мне")
async def process_about_button(message: types.Message):
    logger.info(f"Нажата кнопка Обо мне от {message.from_user.id}")
    await send_log_to_telegram(f"Нажата кнопка Обо мне от {message.from_user.id}")
    await process_about_command(message)

@dp.message(Command("contact"))
async def process_contact_command(message: types.Message):
    logger.info(f"Получена команда /contact от {message.from_user.id}")
    await send_log_to_telegram(f"Команда /contact от {message.from_user.id}")
    await message.answer(
        "<b>Связаться со мной</b>\n"
        "Почта: <a href='mailto:ermilegor@gmail.com'>ermilegor@gmail.com</a>\n"
        "Telegram: <a href='https://t.me/prostof2p'>@prostof2p</a>",
        parse_mode=ParseMode.HTML,
        reply_markup=contact_keyboard
    )
    await message.answer("Быстрые ссылки:", reply_markup=contact_inline_keyboard)

@dp.message(lambda m: m.text == "📩 Связаться")
async def process_contact_button(message: types.Message):
    logger.info(f"Нажата кнопка Связаться от {message.from_user.id}")
    await send_log_to_telegram(f"Нажата кнопка Связаться от {message.from_user.id}")
    await process_contact_command(message)

@dp.message(lambda m: m.text == "⬅️ Назад")
async def process_back(message: types.Message):
    logger.info(f"Нажата кнопка Назад от {message.from_user.id}")
    await send_log_to_telegram(f"Нажата кнопка Назад от {message.from_user.id}")
    await message.answer("Вы вернулись к основному меню.", reply_markup=main_keyboard)

@dp.message()
async def handle_web_app_data(message: types.Message):
    if message.content_type == ContentType.WEB_APP_DATA:
        logger.info(f"Получены данные из Web App от {message.from_user.id}: {message.web_app_data.data}")
        await send_log_to_telegram(f"Получены данные из Web App от {message.from_user.id}: {message.web_app_data.data}")
        try:
            data = json.loads(message.web_app_data.data)
            if data.get('action') == 'back':
                logger.info(f"Получена команда 'back' от {message.from_user.id}")
                await send_log_to_telegram(f"Получена команда 'back' от {message.from_user.id}")
                await message.answer("Вы вернулись к основному меню.", reply_markup=main_keyboard)
                return
            name = data.get('name', 'Не указано')
            msg_text = data.get('message', 'Не указано')
            text = f"<b>Новая заявка (Web App)</b>\nИмя: {name}\nСообщение: {msg_text}\nОт: {message.from_user.id}"
            logger.info(f"Отправляем сообщение администратору {ADMIN_ID}: {text}")
            await send_log_to_telegram(f"Отправляем заявку администратору: {text}")
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode=ParseMode.HTML)
            await message.answer("Ваша заявка отправлена! Я свяжусь с вами скоро.", reply_markup=main_keyboard)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON: {e}")
            await send_log_to_telegram(f"Ошибка JSON: {e}")
            await message.answer("Ошибка обработки заявки. Попробуйте снова.", reply_markup=main_keyboard)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения администратору: {e}")
            await send_log_to_telegram(f"Ошибка отправки заявки: {e}")
            await message.answer("Ошибка сервера. Попробуйте снова позже.", reply_markup=main_keyboard)
    else:
        logger.info(f"Получено неподдерживаемое сообщение от {message.from_user.id}: {message.text}")
        await send_log_to_telegram(f"Неподдерживаемое сообщение от {message.from_user.id}: {message.text}")
        await message.answer(
            "<b>Внимание!</b> Этот бот работает только через кнопки или Web App. Пожалуйста, выбери действие ниже:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard
        )

# --- HTTP-маршруты ---
async def handle_root(request):
    logger.info("Получен запрос на корневой маршрут")
    await send_log_to_telegram("Получен запрос на /")
    return web.Response(text="Bot is running")

async def handle_logs(request):
    logger.info("Получен запрос на просмотр логов")
    await send_log_to_telegram("Запрос на просмотр логов /logs")
    try:
        with open('app.log', 'r') as f:
            logs = f.read()
        return web.Response(text=logs)
    except FileNotFoundError:
        return web.Response(text="Логи не найдены")

async def handle_test(request):
    logger.info("Получен тестовый запрос /test")
    await send_log_to_telegram("Тестовый запрос /test")
    try:
        await bot.send_message(chat_id=ADMIN_ID, text="Тестовое сообщение от сервера main.py")
        return web.Response(text="Тестовое сообщение отправлено в Telegram")
    except Exception as e:
        logger.error(f"Ошибка тестового сообщения: {e}")
        await send_log_to_telegram(f"Ошибка тестового сообщения: {e}")
        return web.Response(text=f"Ошибка: {e}")

async def handle_submit(request):
    logger.info(f"Получен запрос: {request.method} /submit")
    await send_log_to_telegram(f"Получен запрос: {request.method} /submit")
    
    headers_str = ", ".join([f"{key}: {value}" for key, value in request.headers.items()])
    logger.info(f"Заголовки запроса: {headers_str}")
    await send_log_to_telegram(f"Заголовки запроса: {headers_str}")
    
    try:
        raw_data = await request.read()
        data = json.loads(raw_data.decode('utf-8'))
        logger.info(f"Тело запроса: {data}")
        await send_log_to_telegram(f"Тело запроса: {json.dumps(data, ensure_ascii=False)}")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {str(e)}")
        await send_log_to_telegram(f"Ошибка декодирования JSON: {str(e)}")
        return web.Response(text="Ошибка: Неверный формат данных", status=400)

    name = data.get('name', 'Не указано')
    message = data.get('message', 'Не указано')
    
    msg = f"<b>Новая заявка (через сервер)</b>\nИмя: {name}\nСообщение: {message}"
    logger.info(f"Отправляем сообщение администратору {ADMIN_ID}: {msg}")
    await send_log_to_telegram(f"Отправляем сообщение администратору: {msg}")
    
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode=ParseMode.HTML)
        logger.info("Сообщение успешно отправлено")
        await send_log_to_telegram("Сообщение успешно отправлено")
        return web.json_response({"status": "success"})
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        await send_log_to_telegram(f"Ошибка отправки сообщения: {e}")
        return web.Response(text=f"Ошибка: {str(e)}", status=500)

# --- Запуск ---
app = web.Application(middlewares=[cors_middleware])
request_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
request_handler.register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)
app.add_routes([
    web.get('/', handle_root),
    web.get('/logs', handle_logs),
    web.get('/test', handle_test),
    web.post('/submit', handle_submit),
    web.options('/submit', handle_submit)  # Поддержка OPTIONS для CORS
])

async def main():
    logger.info("Запускаем бота с вебхуком...")
    await send_log_to_telegram("Запускаем бота с вебхуком...")
    await set_bot_commands()
    await on_startup()
    app.on_shutdown.append(lambda _: on_shutdown())
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()
    logger.info(f"Сервер запущен на {WEBAPP_HOST}:{WEBAPP_PORT}")
    await send_log_to_telegram(f"Сервер запущен на {WEBAPP_HOST}:{WEBAPP_PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())