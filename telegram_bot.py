import subprocess
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, Message
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties  # Импортируем DefaultBotProperties

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/bot.log"),  # Логи сохраняются в /app/logs/bot.log
        logging.StreamHandler()  # Логи также выводятся в консоль
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = "1472315449:AAEvo2GQrDVOk4jdzStFFKOFNxWqZuIfiR8"
ADMIN_USER_ID = 450271995
ORDER_CHAT_ID = 450271995  # Замените на ID группы или пользователя, куда отправлять заказы

# Инициализация бота и диспетчера
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)  # Указываем parse_mode через DefaultBotProperties
)
dp = Dispatcher()  # Создаем Dispatcher без передачи бота

# Обработчик команды /update
@dp.message(Command("update"))
async def update_products(message: types.Message):
    # Проверяем, является ли пользователь администратором
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("У вас нет прав для выполнения этой команды.")
        return

    # Остальная логика команды
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
        data = json.loads(message.web_app_data.data)
        logger.info(f"Получены данные: {data}")  # Логируем данные

        # Проверяем наличие обязательных полей
        if 'cart_items' not in data or 'name' not in data or 'phone' not in data:
            await message.reply("Ошибка: некорректные данные заказа.")
            return

        cart_items = data['cart_items']
        name = data['name']
        phone = data['phone']

        # Формируем сообщение о заказе
        order_message = f"Новый заказ!\n\nИмя: {name}\nТелефон: {phone}\n\nТовары:\n"
        for item in cart_items:
            order_message += f"{item['name']} - {item['quantity']} x ₽{item['price']}\n"

        # Отправляем сообщение в указанную группу или пользователю
        await bot.send_message(chat_id=ORDER_CHAT_ID, text=order_message)

        # Отправляем фото товаров, если они есть
        for item in cart_items:
            if 'images' in item and item['images']:
                for image in item['images']:
                    with open(image, 'rb') as photo:
                        await bot.send_photo(chat_id=ORDER_CHAT_ID, photo=photo, caption=f"{item['name']} - {item['quantity']} x ₽{item['price']}")
    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {e}")
        await message.reply("Произошла ошибка при обработке заказа.")

# Функция, которая выполняется при запуске бота
async def on_startup():
    logger.info("Бот запущен. Обновляю страницу с товарами...")
    try:
        result = subprocess.run(["python", "generate_html.py"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Страница с товарами успешно обновлена!")
        else:
            logger.error(f"Ошибка при обновлении страницы:\n{result.stderr}")
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")

# Запуск бота
async def main():
    await on_startup()  # Выполняем код при запуске
    await dp.start_polling(bot)  # Передаем бота в start_polling

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())