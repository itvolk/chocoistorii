import os
import uuid
import secrets
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from urllib.parse import unquote
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Request, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, confloat, constr

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
security = HTTPBearer()

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Пути к изображениям
IMAGES_DIR = os.path.abspath("/app/products")
IMAGES_URL = "/products"
os.makedirs(IMAGES_DIR, exist_ok=True)
app.mount(IMAGES_URL, StaticFiles(directory=IMAGES_DIR), name="products")

# Модели данных
class ProductImage(BaseModel):
    url: str
    name: Optional[str] = None

class ProductModel(BaseModel):
    id: constr(min_length=3, max_length=50)
    name: constr(min_length=3, max_length=100)
    price: confloat(gt=0)
    description: constr(max_length=1000) = ""
    images: List[str] = []  # Массив строк с URL

class AdminAuthRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None

class AdminAuthResponse(BaseModel):
    auth_url: str
    expires: str

# Инициализация БД
def init_db():
    with sqlite3.connect('products.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                images TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                telegram_id INTEGER NOT NULL,
                expires TIMESTAMP NOT NULL
            )
        ''')
        conn.commit()

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")

# Генерация токена
def generate_token() -> str:
    return secrets.token_urlsafe(32)

# Проверка прав администратора
async def verify_admin(telegram_id: int):
    with sqlite3.connect('products.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,))
        if not cursor.fetchone():
            logger.warning(f"Access denied for telegram_id: {telegram_id}")
            raise HTTPException(status_code=403, detail="Access denied")

# Проверка токена
async def verify_token(token: str) -> int:
    with sqlite3.connect('products.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT telegram_id FROM auth_tokens WHERE token = ? AND expires > datetime('now')",
            (token,)
        )
        result = cursor.fetchone()
    
    if not result:
        logger.warning(f"Invalid token: {token}")
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    
    return result[0]

# API для генерации ссылки в админку
@app.post("/api/admin/generate-link", response_model=AdminAuthResponse)
async def generate_auth_link(request: AdminAuthRequest):
    try:
        await verify_admin(request.telegram_id)
        token = generate_token()
        expires = (datetime.now() + timedelta(minutes=5)).isoformat()

        with sqlite3.connect('products.db') as conn:
            conn.execute(
                "INSERT OR REPLACE INTO auth_tokens VALUES (?, ?, ?)",
                (token, request.telegram_id, expires)
            )
            conn.commit()

        return {
            "auth_url": f"/admin-panel?token={token}",
            "expires": expires
        }
        
    except Exception as e:
        logger.error(f"Error generating auth link: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# API для проверки токена
@app.get("/api/admin/verify-token")
async def check_auth_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        telegram_id = await verify_token(token)
        return {"status": "success", "telegram_id": telegram_id}
    except HTTPException as he:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# API для получения списка товаров
@app.get("/api/admin/products")
async def get_products(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        telegram_id = await verify_token(credentials.credentials)
        with sqlite3.connect('products.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products")
            products = [dict(row) for row in cursor.fetchall()]

        for product in products:
            if product.get('images'):
                try:
                    product['images'] = json.loads(product['images'])
                except json.JSONDecodeError:
                    product['images'] = []

        return {"products": products}
    except Exception as e:
        logger.error(f"Error getting products: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# API для обновления товара
@app.post("/api/admin/products")
async def update_product(
    product: ProductModel,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        telegram_id = await verify_token(credentials.credentials)
        # Преобразуем абсолютные URL в относительные пути
        processed_images = [
            url.replace(f"{window.location.origin}/", "")  # Для фронтенда
            if url.startswith("http") else url 
            for url in product.images
        ]
        
        # Преобразуем список изображений в JSON-строку
        images_json = json.dumps(processed_images)
        
        with sqlite3.connect('products.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (id, name, price, description, images)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                product.id,
                product.name,
                product.price,
                product.description,
                images_json
            ))
            conn.commit()
        
        return {"status": "success"}
    
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# API для получения конкретного товара
@app.get("/api/admin/products/{product_id}")
async def get_product(
    product_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        decoded_id = unquote(product_id)
        await verify_token(credentials.credentials)

        with sqlite3.connect('products.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM products WHERE id = ?",
                (decoded_id,)
            )
            product = cursor.fetchone()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product_data = dict(product)
        if product_data.get('images'):
            try:
                product_data['images'] = json.loads(product_data['images'])
            except json.JSONDecodeError:
                product_data['images'] = []

        return product_data
    except Exception as e:
        logger.error(f"Error getting product: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# API для загрузки изображений
@app.post("/api/admin/upload")
async def upload_images(
    files: List[UploadFile] = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        await verify_token(credentials.credentials)
        uploaded_files = []

        for file in files:
            file_ext = os.path.splitext(file.filename)[1]
            new_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(IMAGES_DIR, new_filename)

            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            # Сохраняем относительный путь
            uploaded_files.append({
                "filename": f"products/{new_filename}",  # Формат: products/filename.jpg
                "originalname": file.filename
            })

        return {"status": "success", "files": uploaded_files}

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Очистка устаревших токенов
@app.post("/api/admin/clean-tokens")
async def clean_expired_tokens():
    try:
        with sqlite3.connect('products.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auth_tokens WHERE expires < datetime('now')")
            deleted = cursor.rowcount
            conn.commit()

        logger.info(f"Cleaned {deleted} expired tokens")
        return {"deleted": deleted}
    except Exception as e:
        logger.error(f"Error cleaning tokens: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# API для удаления товара
@app.delete("/api/admin/products/{product_id}")
async def delete_product(
    product_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        telegram_id = await verify_token(credentials.credentials)
        decoded_id = unquote(product_id)

        with sqlite3.connect('products.db') as conn:
            cursor = conn.cursor()
            
            # Проверяем существование товара
            cursor.execute("SELECT 1 FROM products WHERE id = ?", (decoded_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Удаляем товар
            cursor.execute("DELETE FROM products WHERE id = ?", (decoded_id,))
            conn.commit()

        return {"status": "success", "message": "Product deleted"}

    except HTTPException as he:
        raise
    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)