# -*- coding: utf-8 -*-
import os
from html import escape

def generate_html():
    products_dir = 'products/'
    products = []
    
    for folder in os.listdir(products_dir):
        folder_path = os.path.join(products_dir, folder)
        if os.path.isdir(folder_path):
            product = {
                'name': escape(folder),
                'price': '0',
                'description': '',
                'images': []
            }
            
            # Чтение price.txt
            price_path = os.path.join(folder_path, 'price.txt')
            if os.path.exists(price_path):
                with open(price_path, 'r') as f:
                    product['price'] = f.read().strip()
            
            # Чтение description.txt
            desc_path = os.path.join(folder_path, 'description.txt')
            if os.path.exists(desc_path):
                with open(desc_path, 'r', encoding='utf-8') as f:
                    product['description'] = escape(f.read().strip())
            
            # Поиск изображений
            images_dir = os.path.join(folder_path, 'images')
            if os.path.isdir(images_dir):
                product['images'] = [
                    os.path.relpath(os.path.join(images_dir, f)) 
                    for f in os.listdir(images_dir) 
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                ]
            
            products.append(product)

    # Генерация HTML
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Магазин шоколада</title>
    <link rel="stylesheet" href="styles.css">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
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
                <button type="submit" class="Button">Отправить заказ</button>
            </form>
        </div>
    </div>

    <button id="open-cart-button" class="cart-button">
        🛒 Корзина
        <span id="cart-counter" class="counter"></span>
    </button>
    <script src="script.js"></script>
</body>
</html>'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML-страница успешно создана!")

if __name__ == "__main__":
    generate_html()