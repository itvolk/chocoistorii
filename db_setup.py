import sqlite3

def setup_database():
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    # Таблица товаров (если не существует)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT,
        images TEXT,
        category TEXT,
        is_active INTEGER DEFAULT 1
    )
    ''')
    
    # Таблица администраторов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_database()