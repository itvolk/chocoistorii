import subprocess
import logging
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = "1472315449:AAEvo2GQrDVOk4jdzStFFKOFNxWqZuIfiR8"
ADMIN_USER_ID = 450271995
ORDER_CHAT_ID = 450271995  # Замените на ID группы или пользователя, куда отправлять заказы

# Обработчик команды /update
async def update_products(update: Update, context):
    # Проверяем, является ли пользователь администратором
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    # Остальная логика команды
    try:
        result = subprocess.run(["python", "generate_html.py"], capture_output=True, text=True)
        if result.returncode == 0:
            await update.message.reply_text("Страница с товарами успешно обновлена!")
        else:
            await update.message.reply_text(f"Ошибка при обновлении страницы:\n{result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {str(e)}")

# Обработчик данных из веб-приложения
async def handle_web_app_data(update: Update, context):
    try:
        data = json.loads(update.message.web_app_data.data)
        logger.info(f"Получены данные: {data}")

        # Проверяем наличие обязательных полей
        if 'cart_items' not in data or 'name' not in data or 'phone' not in data:
            await update.message.reply_text("Ошибка: некорректные данные заказа.")
            return

        cart_items = data['cart_items']
        name = data['name']
        phone = data['phone']

        # Формируем сообщение о заказе
        order_message = f"Новый заказ!\n\nИмя: {name}\nТелефон: {phone}\n\nТовары:\n"
        for item in cart_items:
            order_message += f"{item['name']} - {item['quantity']} x ₽{item['price']}\n"

        # Отправляем сообщение в указанную группу или пользователю
        await context.bot.send_message(chat_id=ORDER_CHAT_ID, text=order_message)

        # Отправляем фото товаров, если они есть
        for item in cart_items:
            if 'images' in item and item['images']:
                for image in item['images']:
                    with open(image, 'rb') as photo:
                        await context.bot.send_photo(chat_id=ORDER_CHAT_ID, photo=photo, caption=f"{item['name']} - {item['quantity']} x ₽{item['price']}")
    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {e}")
        await update.message.reply_text("Произошла ошибка при обработке заказа.")

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

# Создаем приложение и добавляем обработчики
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler("update", update_products))
app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

# Запускаем бота
if __name__ == '__main__':
    # Выполняем код при запуске
    on_startup()
    app.run_polling()