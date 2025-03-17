import subprocess
import logging
import json
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
import asyncio
import signal

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

# Инициализация бота с кастомной сессией
session = AiohttpSession(
    read_timeout=30,
    write_timeout=30,
    connect_timeout=30,
)

bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Обработчик команды /update
@dp.message(Command("update"))
async def update_products(message: types.Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("У вас нет прав для выполнения этой команды.")
        return

    try:
        result = subprocess.run(["python", "generate_html.py"], capture_output=True, text=True)
        if result.returncode == 0:
            await message.reply("Страница с товарами успешно обновлена!")
        else:
            await message.reply(f"Ошибка при обновлении страницы:\n{result.stderr}")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {str(e)}")

# Обработчик данных из веб-приложения
@dp.message(lambda message: message.web_app_data is not None)
async def handle_web_app_data(message: types.Message):
    try:
        logger.info(f"Получены данные из веб-приложения: {message.web_app_data.data}")
        data = json.loads(message.web_app_data.data)

        if not isinstance(data, dict):
            await message.reply("Ошибка: данные должны быть в формате JSON.")
            return

        if 'cartItems' not in data or 'name' not in data or 'phone' not in data:
            await message.reply("Ошибка: некорректные данные заказа. Отсутствуют обязательные поля.")
            return

        if not data['name'] or not data['phone']:
            await message.reply("Ошибка: имя или телефон не указаны.")
            return

        cart_items = data['cartItems']
        name = data['name']
        phone = data['phone']

        order_message = f"Новый заказ!\n\nИмя: {name}\nТелефон: {phone}\n\nТовары:\n"
        for item in cart_items:
            order_message += f"{item['name']} - {item['quantity']} x ₽{item['price']}\n"

        total = sum(item['price'] * item['quantity'] for item in cart_items)
        order_message += f"\nИтого: ₽{total:.2f}"

        await bot.send_message(chat_id=ORDER_CHAT_ID, text=order_message)

        for item in cart_items:
            if 'images' in item and item['images']:
                for image in item['images']:
                    try:
                        with open(image, 'rb') as photo:
                            await bot.send_photo(chat_id=ORDER_CHAT_ID, photo=photo, caption=f"{item['name']} - {item['quantity']} x ₽{item['price']}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке изображения: {e}")
                        await bot.send_message(chat_id=ORDER_CHAT_ID, text=f"Не удалось отправить изображение для товара: {item['name']}")

        await message.reply("Ваш заказ успешно оформлен! Спасибо за покупку.")

    except json.JSONDecodeError:
        logger.error("Ошибка при декодировании JSON данных из веб-приложения.")
        await message.reply("Ошибка: данные из веб-приложения имеют неверный формат.")
    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {e}")
        await message.reply("Произошла ошибка при обработке заказа. Пожалуйста, попробуйте еще раз.")

# Функция, которая выполняется при запуске бота
async def on_startup():
    logger.info("Starting bot initialization...")
    logger.debug(f"Python version: {sys.version}")
    
    try:
        me = await bot.get_me()
        logger.success(f"Bot @{me.username} initialized successfully!")
    except Exception as e:
        logger.critical(f"Bot auth failed: {e}")
        raise

    try:
        result = subprocess.run(["python", "generate_html.py"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Страница с товарами успешно обновлена!")
        else:
            logger.error(f"Ошибка при обновлении страницы:\n{result.stderr}")
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")

# Обработчик сигналов для graceful shutdown
def handle_shutdown(signum, frame):
    logger.info("Received shutdown signal. Stopping bot...")
    asyncio.create_task(shutdown())

async def shutdown():
    await bot.session.close()
    logger.info("Bot session closed properly")
    sys.exit(0)

# Запуск бота
async def main():
    try:
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        await bot.delete_webhook()
        await on_startup()
        await dp.start_polling(
            bot,
            skip_updates=True,
            close_bot_session=True,
            allowed_updates=dp.resolve_used_update_types()
        )
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        await shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}")