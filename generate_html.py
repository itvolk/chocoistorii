 # -*- coding: utf-8 -*-
import os

# Указываем путь к папке с товарами
products_dir = 'image/'

# Создаем список для хранения данных о товарах
products = []

# Проходим по каждой папке в директории
for folder_name in os.listdir(products_dir):
    folder_path = os.path.join(products_dir, folder_name)
    
    # Проверяем, что это папка
    if os.path.isdir(folder_path):
        product_name = folder_name
        price_path = os.path.join(folder_path, 'price.txt')
        description_path = os.path.join(folder_path, 'description.txt')

        # Читаем цену и описание из файлов
        price = 'Цена не указана'
        description = 'Описание отсутствует'

        if os.path.exists(price_path):
            with open(price_path, 'r', encoding='utf-8') as file:
                price = file.read().strip()

        if os.path.exists(description_path):
            with open(description_path, 'r', encoding='utf-8') as file:
                description = file.read().strip()

        # Собираем все изображения из папки
        images = []
        for file_name in os.listdir(folder_path):
            if file_name.startswith('image') and file_name.endswith('.jpg'):
                images.append(os.path.join(folder_path, file_name))

        # Добавляем товар в список
        products.append({
            'name': product_name,
            'images': images,
            'price': price,
            'description': description
        })

# Создаем HTML-код
html_content = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Интернет-магазин</title>
    <link rel="stylesheet" href="styles.css">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
    <!-- Закоментированный код для добавления товаров через JS -->
    <!-- <div class="container"></div> <!-- Контейнер для карточек товаров -->'''

# Добавляем информацию о каждом товаре
for product in products:
    html_content += f'''
    <div class="product">
        <img src="{product[\'image\']}" alt="{product[\'name\']}">
        <h2>{product[\'name\']}</h2>
        <p><strong>Цена:</strong> {product[\'price\']}</p>
        <button class="add-to-cart" onclick="addToCart(this)">В корзину</button>
    </div>
    '''

# Завершаем HTML-код
html_content += '''
    <!-- Кнопка для открытия корзины -->
    <button id="open-cart-button" class="cart-button">Корзина</button>

    <!-- Модальное окно корзины -->
    <div id="cart-modal" class="modal">
        <div class="modal-content">
            <span id="close-cart-button" class="close">&times;</span>
            <h3>Корзина</h3>
            <div id="cart-items"></div>
            <hr>
            <p>Итого: ₽ <span id="total">0</span></p>
            <button id="checkout-button" class="add-to-cart">Оформить заказ</button>
        </div>
    </div>

    <script src="script.js"></script>
</body>
</html>'''

# Сохраняем HTML-файл
with open('index.html', 'w', encoding='utf-8') as file:
    file.write(html_content)

print("HTML-страница успешно создана!")