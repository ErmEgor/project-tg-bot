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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
WEBAPP_PORT = int(os.getenv("PORT", 10000))

# Настройка Google Sheets
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "your_spreadsheet_id_here")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# CORS настройки
ALLOWED_ORIGINS = [
    "https://project-tg-frontend-git-main-ermegors-projects.vercel.app",
    "http://localhost:3000"
]

async def cors_middleware(app, handler):
    async def middleware(request):
        origin = request.headers.get('Origin', '')
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

# --- Google Sheets ---
def get_sheets_service():
    try:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(GOOGLE_SHEETS_CREDENTIALS), scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets: {e}")
        asyncio.create_task(send_log_to_telegram(f"Ошибка подключения к Google Sheets: {e}"))
        raise

async def append_to_sheets(data):
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        values = [[data['name'], data['telegram'], data['description'], data['user_id']]]
        body = {'values': values}
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A:D',
            valueInputOption='RAW',
            body=body
        ).execute()
        logger.info(f"Данные добавлены в Google Sheets: {data}")
        await send_log_to_telegram(f"Новая заявка добавлена в Google Sheets: {data}")
    except Exception as e:
        logger.error(f"Ошибка добавления данных в Google Sheets: {e}")
        await send_log_to_telegram(f"Ошибка добавления данных в Google Sheets: {e}")
        raise

async def get_sheets_data(limit=10):
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A:D'
        ).execute()
        values = result.get('values', [])
        return values[-limit:] if values else []
    except Exception as e:
        logger.error(f"Ошибка чтения данных из Google Sheets: {e}")
        await send_log_to_telegram(f"Ошибка чтения данных из Google Sheets: {e}")
        return []

# --- Определение состояний FSM ---
class OrderForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()

class AdminNotify(StatesGroup):
    waiting_for_message = State()

# --- Клавиатуры ---
main_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Помощь"), KeyboardButton(text="📱 Портфолио")],
        [KeyboardButton(text="ℹ️ Обо мне"), KeyboardButton(text="📩 Связаться")],
        [KeyboardButton(text="💼 Заказать услугу")]
    ],
    resize_keyboard=True
)

admin_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📜 Просмотр логов"), KeyboardButton(text="📋 Заявки")],
        [KeyboardButton(text="📢 Отправить уведомление"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="⬅️ Выход")]
    ],
    resize_keyboard=True
)

portfolio_inline_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="📱 Приложение", web_app=types.WebAppInfo(url="https://project-tg-frontend-git-main-ermegors-projects.vercel.app/")),
        InlineKeyboardButton(text="🌐 Лендинг", url="https://ermegor.github.io/BuildMax/")
    ],
    [
        InlineKeyboardButton(text="🎨 Все работы сразу (Behance)", url="https://www.behance.net/gallery/227197709/portfolio-e-egora")
    ]
])

back_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Назад")]],
    resize_keyboard=True
)

help_keyboard: ReplyKeyboardMarkup = back_keyboard
about_keyboard: ReplyKeyboardMarkup = back_keyboard
contact_keyboard: ReplyKeyboardMarkup = back_keyboard
order_keyboard: ReplyKeyboardMarkup = back_keyboard

contact_inline_keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(inline_keyboard=[
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
        BotCommand(command="order", description="Заказать услугу"),
        BotCommand(command="admin", description="Админ-панель (для админа)")
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
    await message.answer(f"Здравствуй! Что тебя интересует?", reply_markup=main_keyboard)

@dp.message(Command("help"))
async def process_help_command(message: types.Message):
    logger.info(f"Получена команда /help от {message.from_user.id}")
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
    await process_help_command(message)

@dp.message(Command("portfolio"))
async def process_portfolio_command(message: types.Message):
    logger.info(f"Получена команда /portfolio от {message.from_user.id}")
    await message.answer("Выбери проект:", reply_markup=portfolio_inline_keyboard)

@dp.message(lambda m: m.text == "📱 Портфолио")
async def process_portfolio_button(message: types.Message):
    logger.info(f"Нажата кнопка Портфолио от {message.from_user.id}")
    await process_portfolio_command(message)

@dp.message(Command("about"))
async def process_about_command(message: types.Message):
    logger.info(f"Получена команда /about от {message.from_user.id}")
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
    await process_about_command(message)

@dp.message(Command("contact"))
async def process_contact_command(message: types.Message):
    logger.info(f"Получена команда /contact от {message.from_user.id}")
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
    await process_contact_command(message)

@dp.message(lambda m: m.text == "⬅️ Назад")
async def process_back(message: types.Message, state: FSMContext):
    logger.info(f"Нажата кнопка Назад от {message.from_user.id}")
    await state.clear()
    await message.answer("Вы вернулись к основному меню.", reply_markup=main_keyboard)

# --- FSM для заказа ---
@dp.message(lambda m: m.text == "💼 Заказать услугу")
async def process_order_button(message: types.Message, state: FSMContext):
    logger.info(f"Нажата кнопка Заказать услугу от {message.from_user.id}")
    await state.set_state(OrderForm.waiting_for_name)
    await message.answer("Пожалуйста, укажите ваше имя:", reply_markup=order_keyboard)

@dp.message(OrderForm.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    logger.info(f"Получено имя от {message.from_user.id}: {message.text}")
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.waiting_for_description)
    await message.answer("Опишите, какой бот или приложение вам нужен:", reply_markup=order_keyboard)

@dp.message(OrderForm.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    logger.info(f"Получено описание от {message.from_user.id}: {message.text}")
    user_data = await state.get_data()
    telegram_username = f"@{message.from_user.username}" if message.from_user.username else "Не указан"
    
    data = {
        "name": user_data["name"],
        "telegram": telegram_username,
        "description": message.text,
        "user_id": str(message.from_user.id)
    }
    
    try:
        await append_to_sheets(data)
        await message.answer(
            "Ваша заявка успешно отправлена! Я свяжусь с вами скоро.",
            reply_markup=main_keyboard
        )
        admin_msg = (
            f"<b>Новая заявка (FSM)</b>\n"
            f"Имя: {data['name']}\n"
            f"Telegram: {data['telegram']}\n"
            f"Описание: {data['description']}\n"
            f"От: {message.from_user.id}"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Ошибка обработки заявки: {e}")
        await send_log_to_telegram(f"Ошибка обработки заявки: {e}")
        await message.answer(
            "Ошибка при отправке заявки. Попробуйте снова позже.",
            reply_markup=main_keyboard
        )
    finally:
        await state.clear()

# --- Админ-панель ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        logger.info(f"Неавторизованный доступ к админ-панели от {message.from_user.id}")
        await message.answer("У вас нет доступа к админ-панели.", reply_markup=main_keyboard)
        return
    logger.info(f"Админ-панель открыта для {message.from_user.id}")
    await state.clear()
    await message.answer("Добро пожаловать в админ-панель!", reply_markup=admin_keyboard)

@dp.message(lambda m: m.text == "📜 Просмотр логов")
async def view_logs(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа.", reply_markup=main_keyboard)
        return
    logger.info(f"Запрос логов от админа {message.from_user.id}")
    try:
        with open('app.log', 'r', encoding='utf-8') as f:
            logs = f.readlines()[-10:]  # Последние 10 строк
        log_text = "".join(logs) or "Логи пусты."
        await message.answer(f"<b>Последние логи:</b>\n{log_text}", parse_mode=ParseMode.HTML, reply_markup=admin_keyboard)
    except FileNotFoundError:
        await message.answer("Логи не найдены.", reply_markup=admin_keyboard)

@dp.message(lambda m: m.text == "📋 Заявки")
async def view_orders(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа.", reply_markup=main_keyboard)
        return
    logger.info(f"Запрос заявок от админа {message.from_user.id}")
    try:
        orders = await get_sheets_data(limit=5)
        if not orders:
            await message.answer("Заявки отсутствуют.", reply_markup=admin_keyboard)
            return
        response = "<b>Последние заявки:</b>\n"
        for order in orders:
            name = order[0] if len(order) > 0 else "Не указано"
            telegram = order[1] if len(order) > 1 else "Не указано"
            desc = order[2] if len(order) > 2 else "Не указано"
            user_id = order[3] if len(order) > 3 else "Не указано"
            response += f"Имя: {name}\nTelegram: {telegram}\nОписание: {desc}\nUser ID: {user_id}\n---\n"
        await message.answer(response, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при получении заявок: {e}")
        await send_log_to_telegram(f"Ошибка при получении заявок: {e}")
        await message.answer("Ошибка при загрузке заявок.", reply_markup=admin_keyboard)

@dp.message(lambda m: m.text == "📢 Отправить уведомление")
async def start_notification(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа.", reply_markup=main_keyboard)
        return
    logger.info(f"Запрос на отправку уведомления от админа {message.from_user.id}")
    await state.set_state(AdminNotify.waiting_for_message)
    await message.answer("Введите текст уведомления для всех пользователей:", reply_markup=back_keyboard)

@dp.message(AdminNotify.waiting_for_message)
async def send_notification(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа.", reply_markup=main_keyboard)
        await state.clear()
        return
    logger.info(f"Получено уведомление от админа {message.from_user.id}: {message.text}")
    try:
        orders = await get_sheets_data()
        user_ids = {order[3] for order in orders if len(order) > 3 and order[3].isdigit()}
        for user_id in user_ids:
            try:
                await bot.send_message(chat_id=int(user_id), text=f"<b>Уведомление:</b>\n{message.text}", parse_mode=ParseMode.HTML)
                logger.info(f"Уведомление отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        await message.answer("Уведомление отправлено всем пользователям.", reply_markup=admin_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений: {e}")
        await send_log_to_telegram(f"Ошибка при отправке уведомлений: {e}")
        await message.answer("Ошибка при отправке уведомлений.", reply_markup=admin_keyboard)
    finally:
        await state.clear()

@dp.message(lambda m: m.text == "📊 Статистика")
async def view_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа.", reply_markup=main_keyboard)
        return
    logger.info(f"Запрос статистики от админа {message.from_user.id}")
    try:
        orders = await get_sheets_data()
        total_orders = len(orders)
        unique_users = len({order[3] for order in orders if len(order) > 3 and order[3].isdigit()})
        response = (
            f"<b>Статистика:</b>\n"
            f"Всего заявок: {total_orders}\n"
            f"Уникальных пользователей: {unique_users}"
        )
        await message.answer(response, parse_mode=ParseMode.HTML, reply_markup=admin_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await send_log_to_telegram(f"Ошибка при получении статистики: {e}")
        await message.answer("Ошибка при загрузке статистики.", reply_markup=admin_keyboard)

@dp.message(lambda m: m.text == "⬅️ Выход")
async def exit_admin(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа.", reply_markup=main_keyboard)
        return
    logger.info(f"Выход из админ-панели для {message.from_user.id}")
    await state.clear()
    await message.answer("Вы вернулись в главное меню.", reply_markup=main_keyboard)

@dp.message()
async def handle_web_app_data(message: types.Message):
    if message.content_type == ContentType.WEB_APP_DATA:
        logger.info(f"Получены данные из Web App от {message.from_user.id}: {message.web_app_data.data}")
        try:
            data = json.loads(message.web_app_data.data)
            if data.get('action') == 'back':
                logger.info(f"Получена команда 'back' от {message.from_user.id}")
                await message.answer("Вы вернулись к основному меню.", reply_markup=main_keyboard)
                return
            name = data.get('name', 'Не указано')
            contact = data.get('contact', 'Не указано')
            msg_text = data.get('message', 'Не указано')
            text = f"<b>Новая заявка (Web App)</b>\nИмя: {name}\nКонтакт: {contact}\nСообщение: {msg_text}\nОт: {message.from_user.id}"
            logger.info(f"Отправляем сообщение администратору {ADMIN_ID}: {text}")
            await send_log_to_telegram(f"Новая заявка: Имя: {name}, Контакт: {contact}, Сообщение: {msg_text}")
            await bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode=ParseMode.HTML)
            await message.answer("Ваша заявка отправлена! Я свяжусь с вами скоро.", reply_markup=main_keyboard)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON: {e}")
            await send_log_to_telegram(f"Ошибка JSON: {e}")
            await message.answer("Ошибка обработки заявки. Попробуйте снова.", reply_markup=main_keyboard)
        except Exception as e:
            logger.error(f"Ошибка отправки заявки: {e}")
            await send_log_to_telegram(f"Ошибка отправки заявки: {e}")
            await message.answer("Ошибка сервера. Попробуйте снова позже.", reply_markup=main_keyboard)
    else:
        logger.info(f"Получено неподдерживаемое сообщение от {message.from_user.id}: {message.text}")
        await message.answer(
            "<b>Внимание!</b> Этот бот работает только через кнопки или Web App. Пожалуйста, выбери действие ниже:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard
        )

# --- HTTP-маршруты ---
async def handle_root(request):
    logger.info("Получен запрос на корневой маршрут")
    return web.Response(text="Bot is running")

async def handle_logs(request):
    logger.info("Получен запрос на просмотр логов")
    try:
        with open('app.log', 'r') as f:
            logs = f.read()
        return web.Response(text=logs)
    except FileNotFoundError:
        return web.Response(text="Логи не найдены")

async def handle_test(request):
    logger.info("Получен тестовый запрос /test")
    try:
        await bot.send_message(chat_id=ADMIN_ID, text="Тестовое сообщение от сервера main.py")
        return web.Response(text="Тестовое сообщение отправлено в Telegram")
    except Exception as e:
        logger.error(f"Ошибка тестового сообщения: {e}")
        await send_log_to_telegram(f"Ошибка тестового сообщения: {e}")
        return web.Response(text=f"Ошибка: {e}")

async def handle_submit_options(request):
    return web.Response(status=200)

async def handle_submit(request):
    try:
        raw_data = await request.read()
        if not raw_data:
            logger.error("Ошибка: Пустое тело запроса")
            await send_log_to_telegram("Ошибка: Пустое тело запроса")
            return web.Response(text="Ошибка: Пустое тело запроса", status=400)
        data = json.loads(raw_data.decode('utf-8'))
        name = data.get('name', 'Не указано')
        contact = data.get('contact', 'Не указано')
        message = data.get('message', 'Не указано')
        user_id = data.get('user_id', 'Не указано')
        
        msg = f"<b>Новая заявка (через сервер)</b>\nИмя: {name}\nКонтакт: {contact}\nСообщение: {message}\nUser ID: {user_id}"
        logger.info(f"Отправляем сообщение администратору {ADMIN_ID}: {msg}")
        await send_log_to_telegram(f"Новая заявка: Имя: {name}, Контакт: {contact}, Сообщение: {message}, User ID: {user_id}")
        await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode=ParseMode.HTML)
        return web.json_response({"status": "success"})
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {str(e)}")
        await send_log_to_telegram(f"Ошибка декодирования JSON: {str(e)}")
        return web.Response(text="Ошибка: Неверный формат данных", status=400)
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        await send_log_to_telegram(f"Ошибка отправки сообщения: {e}")
        return web.Response(text=f"Ошибка: {str(e)}", status=500)
    
async def handle_ping(request):
    logger.info("Получен пинг-запрос")
    return web.Response(text="Pong")

# --- Запуск ---
app = web.Application(middlewares=[cors_middleware])
request_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
request_handler.register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)
app.add_routes([
    web.get('/', handle_root),
    web.get('/logs', handle_logs),
    web.get('/test', handle_test),
    web.get('/ping', handle_ping),
    web.post('/submit', handle_submit),
    web.options('/submit', handle_submit_options)
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