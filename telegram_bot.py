import logging
import os
import subprocess
import json
from aiogram.types import BotCommand, BotCommandScopeDefault, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
import asyncio
from aiogram.utils.web_app import check_webapp_signature
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Инициализация логов
log_dir = '/app/logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'bot.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Функция для безопасного получения переменных окружения
def get_env_var(name, required=True, default=None, var_type=str):
    value = os.getenv(name, default)
    if required and value is None:
        raise ValueError(f"Необходимо указать переменную окружения {name} в .env файле!")
    try:
        return var_type(value) if value is not None else None
    except (TypeError, ValueError) as e:
        raise ValueError(f"Некорректное значение для {name}: {value}") from e

# Конфигурация с проверками
try:
    ADMIN_ID = get_env_var('ADMIN_ID', var_type=int)
    BOT_TOKEN = get_env_var('BOT_TOKEN')
    ORDER_CHAT_ID = get_env_var('ORDER_CHAT_ID', var_type=int)
    HOST = get_env_var('HOST', required=False, default='0.0.0.0')
    PORT = get_env_var('PORT', required=False, default='8080', var_type=int)
    WEBHOOK_PATH = get_env_var('WEBHOOK_PATH', required=False, default='/webhook')
    BASE_URL = get_env_var('BASE_URL')
    
    logger.info("Все переменные окружения успешно загружены")
except ValueError as e:
    logger.error(f"Ошибка загрузки конфигурации: {e}")
    raise



# Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# Создаем клавиатуру с кнопкой для веб-приложения
async def get_main_keyboard():
    bot_info = await bot.get_me()
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍️ Открыть магазин", web_app={'url': BASE_URL})],
            [KeyboardButton(
                text="Открыть в личном чате", 
                url=f"https://t.me/{bot_info.username}?start=shop"
            )]
        ],
        resize_keyboard=True
    )

# Обработчики сообщений
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    bot_info = await bot.get_me()
    
    if message.chat.type == "private":
        # Личный чат
        await message.answer(
            f"Привет! Добро пожаловать в магазин! \n Для открытия магазина, нажмите кнопку внизу 👇",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🛍️ Открыть магазин", web_app={'url': BASE_URL})]
                ],
                resize_keyboard=True
            )
        )
    else:
        # Группа
        await message.answer(
            "Для работы с магазином перейдите в личный чат с ботом:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🛍️ Открыть магазин",
                            url=f"https://t.me/{bot_info.username}?start=shop"
                        )
                    ]
                ]
            )
        )

@router.message(Command("update"))
async def update_products(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    try:
        process = await asyncio.create_subprocess_exec(
            "python", "generate_html.py",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            await message.answer("Страница с товарами успешно обновлена!")
        else:
            error_msg = stderr.decode().strip() or "Unknown error"
            await message.answer(f"Ошибка при обновлении страницы:\n{error_msg}")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")

@router.message(Command("shop"))
async def shop_handler(message: Message):
    bot_info = await bot.get_me()
    
    if message.chat.type == "private":
        # Личный чат - показываем WebApp кнопку
        await message.answer(
            "Откройте магазин:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🛍️ Открыть магазин", web_app={'url': BASE_URL})]
                ],
                resize_keyboard=True
            )
        )
    else:
        # Группа - предлагаем перейти в личный чат
        await message.answer(
            "Магазин доступен в личном чате с ботом:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🛍️ Открыть магазин",
                            url=f"https://t.me/{bot_info.username}?start=shop"
                        )
                    ]
                ]
            )
        )

@router.message(F.content_type == ContentType.WEB_APP_DATA)
async def handle_web_app_data(message: Message) -> None:
    logger.info(f"Raw web_app_data received: {message.web_app_data}")
    
    try:
        # Логируем сырые данные для диагностики
        logger.info(f"WebApp data content: {message.web_app_data.data}")
        
        # Пытаемся распарсить данные
        try:
            data = json.loads(message.web_app_data.data)
            logger.info(f"Parsed data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            await message.answer("❌ Ошибка в формате данных заказа")
            return

        # Валидация обязательных полей
        required_fields = ['cart_items', 'name', 'phone']
        if not all(field in data for field in required_fields):
            missing = [f for f in required_fields if f not in data]
            logger.error(f"Missing required fields: {missing}")
            await message.answer(f"❌ Отсутствуют обязательные поля: {', '.join(missing)}")
            return

        # Валидация корзины
        if not isinstance(data['cart_items'], list) or len(data['cart_items']) == 0:
            logger.error("Empty or invalid cart items")
            await message.answer("❌ Корзина пуста или содержит ошибки")
            return

        # Подготовка данных заказа
        order_lines = []
        total = 0.0
        
        for item in data['cart_items']:
            try:
                name = str(item['name'])
                price = float(item['price'])
                quantity = int(item['quantity'])
                total += price * quantity
                order_lines.append(f"• {name} × {quantity} - {price:.2f}₽")
            except (KeyError, ValueError) as e:
                logger.error(f"Invalid item format: {item}, error: {e}")
                continue

        if not order_lines:
            await message.answer("❌ Нет валидных товаров в заказе")
            return

        # Формирование сообщения
        order_text = (
            f"🛍️ Новый заказ от {data['name']} ({data['phone']})\n"
            "Состав:\n" + 
            "\n".join(order_lines) +
            f"\n\n💳 Итого: {total:.2f}₽"
        )

        # Отправка админу
        await bot.send_message(
            chat_id=ORDER_CHAT_ID,
            text=order_text,
            parse_mode=ParseMode.HTML
        )
        
        # Ответ пользователю
        await message.answer("✅ Заказ успешно принят! Скоро с вами свяжутся.")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        await message.answer("❌ Произошла непредвиденная ошибка при обработке заказа")

# Обработчик для HTTP fallback
@router.message(F.web_app_data.is_not(None))
async def handle_http_fallback(message: Message):
    logger.info(f"Fallback data: {message.web_app_data}")
    await handle_web_app_data(message)

# временный обработчик для всех входящих сообщений:
@router.message()
async def catch_all(message: Message):
    logger.info(f"Caught message: {message.model_dump_json()}")
    logger.info(f"Content type: {message.content_type}")


async def set_commands():
    commands = [
        BotCommand(command='start', description='Старт'),
        BotCommand(command='update', description='Обновить товары'),
        BotCommand(command='shop', description='Открыть магазин')
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

# Управление вебхуком
async def on_startup() -> None:
    try:
        await bot.delete_webhook()
        await asyncio.sleep(1)
        logger.info("Запуск on_startup...")
        await set_commands()
        result = await bot.set_webhook(
            url=f"{BASE_URL}{WEBHOOK_PATH}",
            allowed_updates=["message", "web_app_data"]  # Важно!
        )
        logger.info(f"Ответ setwebhook: {result}")
        await bot.send_message(ADMIN_ID, "🤖 Бот запущен!")
    except Exception as e:
        logger.error(f"Ошибка в on_startup: {e}")
        raise

async def on_shutdown() -> None:
    await bot.send_message(ADMIN_ID, "🔴 Бот остановлен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

# Health check endpoint
async def health_check(request):
    return web.Response(text="OK")

# Конфигурация приложения
def main():
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    app.router.add_get("/", health_check)
    
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    app.router.add_post(WEBHOOK_PATH, webhook_requests_handler)
    
    setup_application(app, dp, bot=bot)
    web.run_app(app, host=HOST, port=PORT, handle_signals=False)

if __name__ == "__main__":
    main()