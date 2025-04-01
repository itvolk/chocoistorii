import sqlite3
import json
from pathlib import Path

def migrate():
    conn = sqlite3.connect("products.db")
    cursor = conn.cursor()
    
    # Очищаем таблицу перед миграцией (на случай повторного запуска)
    cursor.execute("DELETE FROM products")
    
    # Путь к основной папке с товарами
    products_dir = Path("products")
    
    for product_folder in products_dir.iterdir():
        if not product_folder.is_dir():
            continue  # Пропускаем файлы, если они есть
            
        try:
            product_id = product_folder.name
            name = product_folder.name  # Берем имя из названия папки
            price = float((product_folder / "price.txt").read_text(encoding='utf-8').strip())
            description = (product_folder / "description.txt").read_text(encoding='utf-8').strip()
            
            # Обработка изображений
            images_dir = product_folder / "images"
            images = []
            if images_dir.exists() and images_dir.is_dir():
                for img_file in images_dir.iterdir():
                    if img_file.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                        # Сохраняем относительный путь от корня сайта
                        images.append(f"products/{product_id}/images/{img_file.name}")
            
            # Вставляем в SQLite
            cursor.execute(
                "INSERT INTO products (id, name, price, description, images) VALUES (?, ?, ?, ?, ?)",
                (product_id, name, price, description, json.dumps(images))
            )
            
            print(f"Успешно мигрирован товар: {name}")
            
        except Exception as e:
            print(f"Ошибка при обработке папки {product_folder.name}: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    print("Миграция завершена. Всего товаров:", len(list(products_dir.iterdir())))

if __name__ == "__main__":
    migrate()