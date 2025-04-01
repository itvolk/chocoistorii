# -*- coding: utf-8 -*-
import sqlite3
from html import escape
import json

def generate_html():
    # Подключаемся к базе данных
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    # Получаем все товары из базы
    cursor.execute("SELECT name, price, description, images FROM products")
    products_data = cursor.fetchall()
    conn.close()

    # Формируем список товаров
    products = []
    for name, price, description, images_json in products_data:
        product = {
            'name': escape(name),
            'price': str(price),
            'description': escape(description) if description else '',
            'images': json.loads(images_json) if images_json else []
        }
        products.append(product)

    # Генерация HTML
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Магазин шоколада</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <link rel="stylesheet" href="styles.css">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
    <div class="main-content"> <!-- Новый оберточный div -->
    <div class="container">'''

    for product in products:
        html += f'''
        <div class="product-card" data-name="{product['name']}" data-price="{product['price']}">
            <div class="gallery">
                {"".join(f'<img src="{img}" class="product-image" loading="lazy" alt="{product["name"]}">' for img in product['images'])}
            </div>
            <h3>{product['name']}</h3>
            <p class="price">{product['price']} ₽</p>
            <button class="add-to-cart" onclick="addToCart(this)">В корзину</button>
        </div>'''

    html += '''
    </div>
    </div>
    <!-- Модальные окна -->
    <div id="cart-modal" class="modal">
        <div class="modal-content">
            <span id="close-cart-button" class="close">&times;</span>
            <h3>Ваша корзина</h3>
            <div id="cart-items"></div>
            <div class="total">Итого: <span id="total">0</span> ₽</div>
            <button id="checkout-button" class="Button">Оформить заказ</button>
        </div>
    </div>

    <div id="checkout-modal" class="modal">
        <div class="modal-content">
            <button id="close-checkout-button" class="close">&times;</button>
            <h3>Оформление заказа</h3>
            <form id="checkout-form">
                <input type="text" id="name" placeholder="Имя" required>
                <input type="tel" id="phone" placeholder="Телефон" required>
                <textarea rows="5" type="comment" id="comment" placeholder="Комментарий к заказу"></textarea>
                <button type="submit" class="Button">Отправить заказ</button>
            </form>
        </div>
    </div>
    <div class="cart-button-container">
        <button id="open-cart-button" class="cart-button">
            🛒 Корзина
            <span id="cart-counter" class="counter"></span>
        </button>
    </div>
    <script src="script.js" defer></script>
</body>
</html>'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML-страница успешно создана!")

if __name__ == "__main__":
    generate_html()