import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))



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
    data = update.message.web_app_data.data
    data = json.loads(data)

    message = data['message']
    cart_items = data['cart_items']
    name = data['name']
    phone = data['phone']

    # Отправляем сообщение с данными заказа
    await update.message.reply_text(message)

    # Можно также отправить фото товаров, если они есть
    for item in cart_items:
        if item['images']:
            for image in item['images']:
                with open(image, 'rb') as photo:
                    await update.message.reply_photo(photo, caption=f"{item['name']} - {item['quantity']} x ₽{item['price']}")

# Функция, которая выполняется при запуске бота
async def on_startup(application):
    print("Бот запущен. Обновляю страницу с товарами...")
    await run_generate_html()

# Создаем приложение и добавляем обработчики
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler("update", update_products))
app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

# Запускаем бота и добавляем хук для выполнения кода при запуске бота
app.run_polling(on_startup=on_startup)
