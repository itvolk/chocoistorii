import logging
import os
import subprocess
import json
from datetime import datetime
import aiohttp
from aiogram.types import (
    BotCommand, 
    BotCommandScopeDefault, 
    KeyboardButton, 
    ReplyKeyboardMarkup, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    Chat,
    User,
    Message
)
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
from aiogram.utils.keyboard import InlineKeyboardBuilder
from urllib.parse import quote
from aiogram.types import InputMediaPhoto
from urllib.parse import urlparse
from aiogram.exceptions import TelegramBadRequest
import io
from typing import Optional, Union
from aiogram.types import BufferedInputFile

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

# Обработчик сообщения /start
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

# Обработчик сообщения от веб апп (обработка заказа)
@router.message(F.content_type == ContentType.WEB_APP_DATA)
async def handle_web_app_data(message: Message) -> None:
    try:
        data = json.loads(message.web_app_data.data)
        logger.info(f"Order data: {json.dumps(data, indent=2)}")

        # Валидация данных
        if not all(k in data for k in ['cart_items', 'name', 'phone', 'comment']):
            raise ValueError("Missing required fields")

        # Формируем текст заказа
        order_lines = []
        total = 0
        media_group = []
        unique_images = set()

        for item in data['cart_items']:
            try:
                price = float(item['price'])
                qty = int(item['quantity'])
                item_total = price * qty
                total += item_total
                order_line = f"• {item['name']} × {qty} = {item_total:.2f}₽"
                order_lines.append(order_line)

                # Обрабатываем изображения (максимум 10 уникальных)
                if len(media_group) < 10 and 'photo_url' in item and item['photo_url']:
                    img_url = item['photo_url']
                    if not img_url.startswith(('http://', 'https://')):
                        img_url = f"https://chocoistorii.ru{img_url}" if img_url.startswith('/') else f"https://{img_url}"
                    
                    # Проверяем уникальность изображения
                    if img_url not in unique_images:
                        unique_images.add(img_url)
                        image_data = await download_and_validate_image(img_url)
                        if image_data:
                            media_group.append(
                                InputMediaPhoto(
                                    media=BufferedInputFile(
                                        file=image_data.getvalue(),
                                        filename=f"product_{len(media_group)}.jpg"
                                    )
                                )
                            )
                        
            except Exception as e:
                logger.error(f"Error processing item: {str(e)}")
                continue

        # Формируем итоговый текст
        if {data['comment']} == "":
            order_text = (
                f"🛍️ Новый заказ от {data['name']}\n"
                f"📞 Телефон: {data['phone']}\n\n"
                "Состав заказа:\n" + "\n".join(order_lines) + 
                f"\n\n💳 Итого: {total:.2f}₽"
            )
        else:
            order_text = (
                f"🛍️ Новый заказ от {data['name']}\n"
                f"📞 Телефон: {data['phone']}\n\n"
                "Состав заказа:\n" + "\n".join(order_lines) + 
                f"\n\n💳 Итого: {total:.2f}₽"
                f"\n\n💬 комментарий к заказу:\n"
                f"{data['comment']}"
            )

        # Добавляем текст к первому изображению
        if media_group:
            media_group[0].caption = order_text
            try:
                await bot.send_media_group(
                    chat_id=ORDER_CHAT_ID,
                    media=media_group
                )
            except Exception as e:
                logger.error(f"Media group error: {str(e)}")
                await send_order_with_first_image(order_text, media_group)
        else:
            await send_text_order(order_text)

        await message.answer("✅ Заказ успешно принят!")

    except Exception as e:
        logger.error(f"Order processing error: {str(e)}")
        await message.answer("❌ Ошибка при обработке заказа")

async def send_order_with_first_image(text: str, media_group: list):
    """Fallback: отправляет первое изображение с текстом"""
    try:
        if media_group:
            await bot.send_photo(
                chat_id=ORDER_CHAT_ID,
                photo=media_group[0].media,
                caption=text
            )
        else:
            await send_text_order(text)
    except Exception as e:
        logger.error(f"Photo send error: {str(e)}")
        await send_text_order(text)

async def send_text_order(text: str):
    """Отправляет текстовый вариант заказа"""
    try:
        await bot.send_message(
            chat_id=ORDER_CHAT_ID,
            text=text
        )
        logger.info("Text order sent")
    except Exception as e:
        logger.error(f"Text order send error: {str(e)}")
        raise

async def send_order_with_images(order_text: str, images: list):
    """Отправляет заказ с несколькими изображениями"""
    try:
        # Отправляем первое изображение с текстом заказа
        first_image = images[0]
        await bot.send_photo(
            chat_id=ORDER_CHAT_ID,
            photo=BufferedInputFile(
                file=first_image.getvalue(),
                filename="product_1.jpg"
            ),
            caption=order_text
        )
        
        # Отправляем остальные изображения (если есть)
        for i, image_data in enumerate(images[1:], start=2):
            await bot.send_photo(
                chat_id=ORDER_CHAT_ID,
                photo=BufferedInputFile(
                    file=image_data.getvalue(),
                    filename=f"product_{i}.jpg"
                )
            )
            
    except Exception as e:
        logger.error(f"Error sending images: {e}")
        await send_text_order(order_text)
        
async def send_order_with_image(text: str, image_url: str):
    """Отправляет заказ с одним изображением"""
    try:
        await bot.send_photo(
            chat_id=ORDER_CHAT_ID,
            photo=image_url,
            caption=text
        )
    except Exception as e:
        logger.error(f"Photo send error: {e}")
        await bot.send_message(
            chat_id=ORDER_CHAT_ID,
            text=text
        )

async def send_order_with_preview(order_text: str, image_url: str, data: dict):
    """Отправляет заказ с превью изображения"""
    try:
        await bot.send_photo(
            chat_id=ORDER_CHAT_ID,
            photo=image_url,
            caption=order_text
        )
    except Exception as e:
        logger.error(f"Photo send error: {e}")
        # Final fallback - только текст
        await bot.send_message(
            chat_id=ORDER_CHAT_ID,
            text=order_text
        )

async def is_valid_image_url(url: str) -> bool:
    """Проверяет валидность URL изображения"""
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False
            
        # Проверяем расширение файла
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        if not any(parsed.path.lower().endswith(ext) for ext in valid_extensions):
            return False
            
        return True
    except Exception:
        return False

async def is_valid_telegram_image(url: str) -> bool:
    """Проверяет, будет ли Telegram принимать это изображение"""
    try:
        # Проверяем расширение файла
        if not url.lower().endswith(('.jpg', '.jpeg', '.png')):
            return False
            
        # Проверяем доступность
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return False
                
                # Telegram требует Content-Type и размер файла
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    return False
                    
                # Проверяем размер файла (до 5MB)
                content_length = int(response.headers.get('Content-Length', 0))
                if content_length > 5 * 1024 * 1024:
                    return False
                    
                # Читаем первые 128 байт для проверки сигнатуры
                chunk = await response.content.read(128)
                if not chunk:
                    return False
                    
                # Проверяем сигнатуры форматов
                if chunk.startswith(b'\xFF\xD8') or chunk.startswith(b'\x89PNG'):
                    return True
                    
        return False
    except Exception as e:
        logger.error(f"Image validation error: {e}")
        return False

async def download_and_validate_image(url: str) -> Union[io.BytesIO, None]:
    """Загружает изображение и проверяет его валидность"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Image download failed: HTTP {response.status}")
                    return None
                
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    logger.error(f"Invalid content type: {content_type}")
                    return None
                
                image_data = io.BytesIO(await response.read())
                header = image_data.read(4)
                image_data.seek(0)
                
                # Проверяем сигнатуры JPEG и PNG
                if header.startswith(b'\xFF\xD8') or header.startswith(b'\x89PNG'):
                    return image_data
                
                logger.error("Invalid image signature")
                return None
    except Exception as e:
        logger.error(f"Image download error: {str(e)}")
        return None

# Обработчик сообщения /shop (открытие мини апп приложения)
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

# Обработчик для HTTP fallback
@router.message(F.web_app_data.is_not(None))
async def handle_http_fallback(message: Message):
    logger.info(f"Fallback data: {message.web_app_data}")
    await handle_web_app_data(message)

# Обработчик сообщения /update (перегенерировать html)
@router.message(Command("update"))
async def update_products(message: Message = None, bot_instance: Bot = None) -> None:
    """Обработчик команды /update, может вызываться как из сообщения, так и программно"""
    bot_to_use = bot_instance or bot  # Используем переданный бот или глобальный
    
    if message and message.from_user.id != ADMIN_ID:
        await bot_to_use.send_message(
            chat_id=message.chat.id,
            text="У вас нет прав для выполнения этой команды."
        )
        return

    try:
        process = await asyncio.create_subprocess_exec(
            "python", "generate_html.py",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()  # Исправлено здесь
        
        if process.returncode == 0:
            success_msg = "Страница с товарами успешно обновлена!"
            logger.info(success_msg)
            if message:
                await bot_to_use.send_message(
                    chat_id=message.chat.id,
                    text=success_msg
                )
        else:
            error_msg = stderr.decode().strip() or "Unknown error"
            logger.error(f"Ошибка при обновлении страницы: {error_msg}")
            if message:
                await bot_to_use.send_message(
                    chat_id=message.chat.id,
                    text=f"Ошибка при обновлении страницы:\n{error_msg}"
                )
    except Exception as e:
        logger.error(f"Произошла ошибка: {str(e)}")
        if message:
            await bot_to_use.send_message(
                chat_id=message.chat.id,
                text=f"Произошла ошибка: {str(e)}"
            )

# Обработчик сообщения /admin (запустить админ.панель)
@router.message(Command("admin"))
async def admin_command(message: Message):
    """Обработчик команды /admin"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав доступа")
        return
    
    try:
        # Используем aiohttp.ClientSession
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BASE_URL}/api/admin/generate-link",
                json={
                    "telegram_id": message.from_user.id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name
                }
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    # Создаем кнопку с ссылкой
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="🔐 Открыть админ-панель",
                            url=f"{BASE_URL}{data['auth_url']}"  # Полный URL
                        )
                    ]])
                    
                    await message.answer(
                        "Админ-панель готова (ссылка действительна 5 минут):",
                        reply_markup=keyboard
                    )
                else:
                    await message.answer("⚠️ Ошибка при генерации ссылки")
                    
    except Exception as e:
        logger.error(f"Error in /admin command: {e}", exc_info=True)
        await message.answer("🚫 Произошла ошибка, попробуйте позже")

# # Временный обработчик для всех входящих сообщений
# @router.message()
# async def catch_all(message: Message):
#     logger.info(f"Caught message: {message.model_dump_json()}")
#     logger.info(f"Content type: {message.content_type}")

# Установка меню команд
async def set_commands():
    commands = [
        BotCommand(command='start', description='Старт'),
        BotCommand(command='update', description='Обновить товары'),
        BotCommand(command='shop', description='Открыть магазин'),
        BotCommand(command='admin', description='Админ-панель (только для админов)')
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


# Функция при запуске
async def on_startup() -> None:
    try:
        await bot.delete_webhook()
        await asyncio.sleep(1)
        logger.info("Запуск on_startup...")
        await set_commands()
        
        # Создаем фейковое сообщение от админа для вызова update
        fake_update_message = Message(
            message_id=0,
            date=datetime.now(),
            chat=Chat(id=ADMIN_ID, type="private"),
            from_user=User(id=ADMIN_ID, is_bot=False, first_name="System"),
            text="/update"
        )
        
        # Вызываем обработчик update с явной передачей бота
        await update_products(fake_update_message, bot)
        
        # Устанавливаем вебхук
        webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
        logger.info(f"Устанавливаем вебхук на URL: {webhook_url}")
        
        result = await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "web_app_data"]
        )
        logger.info(f"Ответ setwebhook: {result}")
        await bot.send_message(ADMIN_ID, "🤖 Бот запущен!")
    except Exception as e:
        logger.error(f"Ошибка в on_startup: {e}", exc_info=True)
        try:
            await bot.send_message(ADMIN_ID, f"⚠️ Ошибка при запуске бота: {str(e)}")
        except Exception as send_error:
            logger.error(f"Не удалось отправить сообщение об ошибке: {send_error}")
        raise

# Функция при остановке
async def on_shutdown() -> None:
    await bot.send_message(ADMIN_ID, "🔴 Бот остановлен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

async def health_check(request):
    return web.Response(text="OK")


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