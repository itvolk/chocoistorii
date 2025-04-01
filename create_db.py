import sqlite3
from pathlib import Path

# Подключаемся к базе (или создаём новую)
DB_PATH = Path("products.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Создаём таблицу товаров
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    description TEXT,
    images TEXT  -- JSON-массив путей к изображениям
)
""")

conn.commit()
conn.close()