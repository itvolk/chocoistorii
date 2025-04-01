const BASE_URL = 'https://chocoistorii.ru';
const IMAGES_URL = '/products';
const tg = window.Telegram?.WebApp;
let authToken = null;
let currentImages = [];


// для отладки
console.log("product-form:", document.getElementById('product-form'));
console.log("product-id:", document.getElementById('product-id'));
console.log("product-name:", document.getElementById('product-name'));
console.log("product-price:", document.getElementById('product-price'));
console.log("product-description:", document.getElementById('product-description'));

document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    authToken = urlParams.get('token');
    
    if (!authToken) {
        showAuthError();
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/verify-token`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!response.ok) throw new Error('Недействительный токен');
        
        const data = await response.json();
        console.log('Успешная авторизация для:', data.telegram_id);
        
        document.getElementById('admin-panel').style.display = 'block';
        if (window.Telegram?.WebApp) window.Telegram.WebApp.expand();
        
        await loadProducts();
        initEventHandlers();
        
    } catch (error) {
        console.error('Ошибка инициализации:', error);
        showAuthError();
    }
});

function initEventHandlers() {
    document.getElementById('image-upload').addEventListener('change', handleImageSelect);
    document.getElementById('upload-images-btn').addEventListener('click', uploadSelectedImages);
    document.getElementById('product-form').addEventListener('submit', handleFormSubmit);
}

function handleImageSelect(event) {
    const files = event.target.files;
    if (!files.length) return;
    
    Array.from(files).forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
            currentImages.push({
                url: e.target.result,
                id: Math.random().toString(36).substr(2, 9),
                file: file,
                isNew: true
            });
            renderProductImages();
        };
        reader.readAsDataURL(file);
    });
}

async function uploadSelectedImages() {
    try {
        const imagesToUpload = currentImages.filter(img => img.isNew);
        if (!imagesToUpload.length) {
            showNotification('Нет новых изображений для загрузки');
            return [];
        }

        showNotification('Начата загрузка изображений...');
        
        const formData = new FormData();
        imagesToUpload.forEach(img => formData.append('files', img.file));

        const response = await fetch('/api/admin/upload', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Ошибка загрузки');
        }

        const result = await response.json();
        
        if (!result?.files) throw new Error('Некорректный ответ сервера');

        currentImages = currentImages.map(img => {
            if (img.isNew) {
                const uploaded = result.files.find(f => f.originalname === img.file.name);
                if (uploaded) {
                    // Нормализация имени файла
                    const filename = uploaded.filename
                        .replace(/^\/+/g, '') // Удалить начальные слеши
                        .replace(/^products\//, ''); // Удалить префикс products/
                        
                    return { 
                        ...img, 
                        url: `${BASE_URL}/products/${filename}`,
                        isNew: false 
                    };
                }
            }
            return img;
        });
        
        renderProductImages();
        showNotification('Изображения успешно загружены!');
        document.getElementById('image-upload').value = '';
        
        return result.files;

    } catch (error) {
        console.error('Ошибка загрузки:', error);
        showNotification(`Ошибка загрузки: ${error.message}`);
        return [];
    }
}

// Обновленный обработчик отправки формы
async function handleFormSubmit(event) {
    event.preventDefault();
    
    try {
        const productData = {
            id: document.getElementById('product-id').value || generateId(),
            name: document.getElementById('product-name').value.trim(),
            price: parseFloat(document.getElementById('product-price').value),
            description: document.getElementById('product-description').value.trim(),
            images: currentImages.map(img => {
                try {
                    const urlObj = new URL(img.url);
                    return urlObj.pathname;
                } catch (e) {
                    const cleanPath = img.url.replace(BASE_URL, '');
                    return cleanPath.startsWith('/') ? cleanPath : `/${cleanPath}`;
                }
            }).filter(path => path)
        };

        if (!productData.name || isNaN(productData.price) || productData.price <= 0) {
            throw new Error('Заполните название и цену (должна быть больше 0)');
        }

        const response = await fetch('/api/admin/products', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(productData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Неизвестная ошибка');
        }

        showNotification('Товар успешно сохранён!');
        await loadProducts();
        clearForm();
        
    } catch (error) {
        console.error('Ошибка:', error);
        showNotification(`Ошибка: ${error.message}`);
    }
}

function generateId() {
    return 'prod_' + Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function renderProductImages() {
    const container = document.getElementById('product-images-container');
    container.innerHTML = currentImages.length ? '' : '<p>Нет изображений</p>';
    
    currentImages.forEach(img => {
        const imgDiv = document.createElement('div');
        imgDiv.className = 'product-image';
        imgDiv.innerHTML = `
            <img src="${img.url}" class="product-image" alt="Превью">
            <button onclick="removeImage('${img.id}')">×</button>
            ${img.isNew ? '<span class="upload-pending">!</span>' : ''}
        `;
        container.appendChild(imgDiv);
    });
}

window.removeImage = function(id) {
    currentImages = currentImages.filter(img => img.id !== id);
    renderProductImages();
};

window.clearForm = function() {
    document.getElementById('product-form').reset();
    currentImages = [];
    renderProductImages();
    showNotification('Форма очищена');
};

// Показать ошибку авторизации
function showAuthError() {
    document.getElementById('auth-error').style.display = 'block';
    document.getElementById('back-to-bot').addEventListener('click', () => {
        window.location.href = 'https://t.me/YourBotName?start=admin';
    });
}

// Показать уведомление
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Загрузка товаров
async function loadProducts() {
    try {
        // Убедитесь, что используете тот же токен, что и при проверке
        const token = localStorage.getItem('admin_token') || authToken;
        
        const response = await fetch('/api/admin/products', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка загрузки товаров');
        }
        
        const data = await response.json();
        renderProducts(data.products);
    } catch (error) {
        console.error('Error:', error);
        showNotification(error.message);
        // Попробуйте переавторизоваться при 403 ошибке
        if (error.message.includes('403')) {
            window.location.reload();
        }
    }
}

// Отображение товаров
function renderProducts(products) {
    const container = document.getElementById('products-container');
    container.innerHTML = '';

    products.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'product-card';
        
        const safeImages = (product.images || []).map(img => {
            return typeof img === 'string' ? { url: img } : img;
        });

        productCard.innerHTML = `
            <div class="product-header">
                <h3>${product.name}</h3>
                <span class="price">${product.price.toFixed(2)} ₽</span>
            </div>
            <div class="product-images">
                ${safeImages.map(img => {
                    const url = img.url || '';
                    if (url.startsWith('http')) {
                        return `<img src="${url}" class="product-image" alt="${product.name}">`;
                    }
                    const finalUrl = url.startsWith('/') ? url : `/${url}`;
                    return `<img src="${finalUrl}" alt="${product.name}">`;
                }).join('')}
            </div>
            <p class="description">${product.description}</p>
            <button class="edit-btn" onclick="editProduct('${product.id.replace(/'/g, "\\'")}')">✏️ Редактировать</button>
            <button class="delete-btn" onclick="deleteProduct('${product.id.replace(/'/g, "\\'")}')">❌ Удалить</button>
        `;
        container.appendChild(productCard);
    });
}

// Редактирование товара
window.editProduct = async function(productId) {
    try {
        const response = await fetch(`/api/admin/products/${encodeURIComponent(productId)}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) throw new Error('Ошибка загрузки товара');
        const product = await response.json();

        // Исправление 4: Обработка изображений
        currentImages = (product.images || []).map(img => {
            const rawUrl = typeof img === 'object' ? img.url : img;
            const url = rawUrl.startsWith('/') 
                ? `${BASE_URL}${rawUrl}`
                : rawUrl.startsWith('http')
                    ? rawUrl
                    : `${BASE_URL}/${rawUrl}`;
            
            return {
                url: url,
                id: Math.random().toString(36).slice(2),
                isNew: false
            };
        });

        // Заполнение полей формы
        document.getElementById('product-id').value = product.id;
        document.getElementById('product-name').value = product.name || '';
        document.getElementById('product-price').value = product.price || '';
        document.getElementById('product-description').value = product.description || '';
        renderProductImages();

    } catch (error) {
        console.error('Ошибка:', error);
        showNotification(error.message);
    }
};

// Добавляем функцию удаления товара
window.deleteProduct = async function(productId) {
    if (!confirm('Вы уверены, что хотите удалить этот товар?')) return;

    try {
        const response = await fetch(`/api/admin/products/${encodeURIComponent(productId)}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });

        const responseData = await response.json(); // Всегда парсим JSON

        if (!response.ok) {
            throw new Error(responseData.detail || `HTTP error! status: ${response.status}`);
        }

        showNotification('Товар успешно удалён!');
        await loadProducts();

    } catch (error) {
        console.error('Ошибка удаления:', error);
        showNotification(`Ошибка: ${error.message}`);
    }
};