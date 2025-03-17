import os
import sys
import fcntl
import logging
import asyncio
import signal
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

router = Router()

# Функция для установки командного меню для бота
async def set_commands():
    # Создаем список команд, которые будут доступны пользователям
    commands = [BotCommand(command='start', description='Старт')]
    # Устанавливаем эти команды как дефолтные для всех пользователей
    await bot.set_my_commands(commands, BotCommandScopeDefault())


# Функция, которая будет вызвана при запуске бота
async def on_startup() -> None:
    # Устанавливаем командное меню
    await set_commands()
    # Устанавливаем вебхук для приема сообщений через заданный URL
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
    # Отправляем сообщение администратору о том, что бот был запущен
    await bot.send_message(chat_id=ADMIN_USER_ID, text='Бот запущен!')


# Функция, которая будет вызвана при остановке бота
async def on_shutdown() -> None:
    # Отправляем сообщение администратору о том, что бот был остановлен
    await bot.send_message(chat_id=ADMIN_USER_ID, text='Бот остановлен!')
    # Удаляем вебхук и, при необходимости, очищаем ожидающие обновления
    await bot.delete_webhook(drop_pending_updates=True)
    # Закрываем сессию бота, освобождая ресурсы
    await bot.session.close()




    

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = "1472315449:AAEvo2GQrDVOk4jdzStFFKOFNxWqZuIfiR8"
ADMIN_USER_ID = 450271995
ORDER_CHAT_ID = 450271995
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://chocoistorii.ru" + WEBHOOK_PATH  # Замените на ваш домен
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8080

# Блокировка файла для предотвращения дублирующих запусков
def singleton():
    lock_file = '/tmp/bot.lock'
    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.critical("Another instance is already running. Exiting.")
        sys.exit(1)

# Инициализация бота
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Инициализация диспетчера
dp = Dispatcher()  # Исправлено: создаем Dispatcher без передачи бота

# функция для реагирования на команду /start
@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Привет, <b>{message.from_user.full_name}</b>! Как дела?")

# Обработчик команды /update
@dp.message(Command("update"))
async def update_products(message: types.Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("Access denied.")
        return

    try:
        proc = await asyncio.create_subprocess_exec(
            "python", "generate_html.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            await message.reply("Products updated successfully!")
        else:
            await message.reply(f"Update failed:\n{stderr.decode()}")
    except Exception as e:
        logger.error(f"Update error: {e}")
        await message.reply(f"Error: {str(e)}")

# Обработчик данных из веб-приложения
@dp.message(lambda message: message.web_app_data is not None)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        
        # Валидация данных
        required_fields = {'cartItems', 'name', 'phone'}
        if not all(field in data for field in required_fields):
            return await message.reply("Missing required fields")
        
        if not data['name'] or not data['phone']:
            return await message.reply("Invalid contact information")

        # Формирование заказа
        order_message = (
            "New Order!\n\n"
            f"Name: {data['name']}\n"
            f"Phone: {data['phone']}\n\n"
            "Items:\n"
        )
        total = 0
        for item in data['cartItems']:
            order_message += f"{item['name']} - {item['quantity']} x ₽{item['price']}\n"
            total += item['price'] * item['quantity']
        
        order_message += f"\nTotal: ₽{total:.2f}"
        
        # Отправка заказа
        await bot.send_message(ORDER_CHAT_ID, order_message)
        await message.reply("Order processed successfully!")

    except json.JSONDecodeError:
        await message.reply("Invalid data format")
    except Exception as e:
        logger.error(f"Order processing error: {e}")
        await message.reply("Order processing failed")

# Настройка вебхука при запуске
async def on_startup(bot: Bot):
    await bot.delete_webhook()
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook set successfully")

# Graceful shutdown
async def shutdown():
    try:
        await dp.storage.close()
        await bot.session.close()
        logger.info("Resources released successfully")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
    finally:
        sys.exit(0)

# Обработчик сигналов
def handle_signal(signum, frame):
    logger.info(f"Received signal {signum}")
    asyncio.create_task(shutdown())

# Основная функция
async def main():
    singleton()  # Проверка дублирующих запусков
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Настройка веб-сервера
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # Запускаем веб-сервер на указанном хосте и порте (из интернета)
    web.run_app(app, host=HOST, port=PORT)

    # # Запуск веб-сервера
    # runner = web.AppRunner(app)
    # await runner.setup()
    # site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    # await site.start()

    # # Установка вебхука
    # await on_startup(bot)

    logger.info(f"Bot started on {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    await asyncio.Event().wait()  # Бесконечное ожидание

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}")