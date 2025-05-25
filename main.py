import asyncio
import json
import os
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

TOKEN = "7711881075:AAHIzBzogyLUSeitdeWzR2Ahq-KpN1MTR9U"
ADMIN_ID = 7586559527  # Проверьте, что это ваш ID
WEBHOOK_HOST = "https://project-tg-bot.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- Клавиатуры (без изменений) ---

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Помощь"), KeyboardButton(text="📱 Портфолио")],
        [KeyboardButton(text="ℹ️ Обо мне"), KeyboardButton(text="📩 Связаться")]
    ],
    resize_keyboard=True
)

portfolio_inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="📱 Приложение", web_app=types.WebAppInfo(url="https://project-tg-frontend-git-main-ermegors-projects.vercel.app")),
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
    print("Команды бота установлены")

# --- Настройка вебхука ---

async def on_startup():
    print("Проверяем и настраиваем вебхук...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("Существующий вебхук удален")
        webhook_info = await bot.get_webhook_info()
        print(f"Текущее состояние вебхука: {webhook_info}")
        if webhook_info.url:
            raise Exception("Вебхук не был удален!")
    except Exception as e:
        print(f"Ошибка при удалении вебхука: {e}")
        raise

    try:
        await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
        print(f"Вебхук установлен на {WEBHOOK_URL}")
        webhook_info = await bot.get_webhook_info()
        print(f"Подтверждение установки вебхука: {webhook_info}")
        if webhook_info.url != WEBHOOK_URL:
            raise Exception("Вебхук не установлен корректно!")
    except Exception as e:
        print(f"Ошибка при установке вебхука: {e}")
        raise

async def on_shutdown():
    print("Удаляем вебхук...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("Вебхук удален")
    except Exception as e:
        print(f"Ошибка при удалении вебхука на завершении: {e}")
    await bot.session.close()
    print("Сессия бота закрыта")

# --- Обработчики ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    print(f"Получена команда /start от {message.from_user.id}")
    await message.answer(f"Ваш ID: {message.from_user.id}\nЗдравствуй! Выбери действие:", reply_markup=main_keyboard)

@dp.message(Command("help"))
async def process_help_command(message: types.Message):
    print(f"Получена команда /help от {message.from_user.id}")
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
    print(f"Нажата кнопка Помощь от {message.from_user.id}")
    await process_help_command(message)

@dp.message(Command("portfolio"))
async def process_portfolio_command(message: types.Message):
    print(f"Получена команда /portfolio от {message.from_user.id}")
    await message.answer("Выбери проект:", reply_markup=portfolio_inline_keyboard)

@dp.message(lambda m: m.text == "📱 Портфолио")
async def process_portfolio_button(message: types.Message):
    print(f"Нажата кнопка Портфолио от {message.from_user.id}")
    await process_portfolio_command(message)

@dp.message(Command("about"))
async def process_about_command(message: types.Message):
    print(f"Получена команда /about от {message.from_user.id}")
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
    print(f"Нажата кнопка Обо мне от {message.from_user.id}")
    await process_about_command(message)

@dp.message(Command("contact"))
async def process_contact_command(message: types.Message):
    print(f"Получена команда /contact от {message.from_user.id}")
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
    print(f"Нажата кнопка Связаться от {message.from_user.id}")
    await process_contact_command(message)

@dp.message(lambda m: m.text == "⬅️ Назад")
async def process_back(message: types.Message):
    print(f"Нажата кнопка Назад от {message.from_user.id}")
    await message.answer("Вы вернулись к основному меню.", reply_markup=main_keyboard)

# Обработка данных из Web App
@dp.message()
async def handle_web_app_data(message: types.Message):
    if message.content_type == ContentType.WEB_APP_DATA:
        print(f"Получены данные из Web App от {message.from_user.id}: {message.web_app_data.data}")
        try:
            data = json.loads(message.web_app_data.data)
            name = data.get('name', 'Не указано')
            msg_text = data.get('message', 'Не указано')
            text = f"<b>Новая заявка (Web App)</b>\nИмя: {name}\nСообщение: {msg_text}\nОт: {message.from_user.id}"
            print(f"Отправляем сообщение администратору {ADMIN_ID}: {text}")
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode=ParseMode.HTML)
            await message.answer("Ваша заявка отправлена! Я свяжусь с вами скоро.", reply_markup=main_keyboard)
        except json.JSONDecodeError as e:
            print(f"Ошибка JSON: {e}")
            await message.answer("Ошибка обработки заявки. Попробуйте снова.", reply_markup=main_keyboard)
        except Exception as e:
            print(f"Ошибка отправки сообщения администратору: {e}")
            await message.answer("Ошибка сервера. Попробуйте снова позже.", reply_markup=main_keyboard)

# Обработчик POST-запроса
async def handle_submit(request):
    try:
        data = await request.json()
        print(f"Получен POST-запрос: {data}")
        name = data.get('name', 'Не указано')
        msg_text = data.get('message', 'Не указано')
        text = f"<b>Новая заявка (через сервер)</b>\nИмя: {name}\nСообщение: {msg_text}"
        print(f"Отправляем сообщение администратору {ADMIN_ID}: {text}")
        await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode=ParseMode.HTML)
        return web.json_response({'status': 'success'})
    except json.JSONDecodeError as e:
        print(f"Ошибка JSON в POST-запросе: {e}")
        return web.json_response({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Ошибка обработки POST-запроса: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=400)

# Ловим все остальные сообщения
@dp.message()
async def default_handler(message: types.Message):
    if message.content_type == ContentType.WEB_APP_DATA:
        return
    print(f"Получено сообщение от {message.from_user.id}: {message.text}")
    await message.answer(
        "<b>Внимание!</b> Этот бот работает только через кнопки. Пожалуйста, выбери действие ниже:",
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard
    )

# --- Запуск ---
app = web.Application()
request_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
request_handler.register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

async def main():
    print("Запускаем бота с вебхуком...")
    await set_bot_commands()
    await on_startup()
    app.on_shutdown.append(lambda _: on_shutdown())
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()
    print(f"Сервер запущен на {WEBAPP_HOST}:{WEBAPP_PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())