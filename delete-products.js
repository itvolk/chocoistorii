const tg = window.Telegram.WebApp;

// Функция для загрузки товаров
async function loadProducts() {
    const response = await fetch('https://your-api.com/products'); // Замените на ваш API
    const products = await response.json();
    renderProducts(products);
}

// Функция для отрисовки товаров
function renderProducts(products) {
    const container = document.getElementById('products-container');
    container.innerHTML = ''; // Очищаем контейнер

    products.forEach(product => {
        const productCard = `
            <div class="product-card">
                <img src="${product.image}" class="product-image" alt="${product.name}">
                <h3>${product.name}</h3>
                <p>Цена: $<span class="price">${product.price}</span></p>
                <button class="remove-product" onclick="deleteProduct(${product.id})">Удалить</button>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', productCard);
    });
}

// Функция для удаления товара
async function deleteProduct(productId) {
    await fetch(`https://your-api.com/products/${productId}`, {
        method: 'DELETE',
    });
    loadProducts(); // Перезагружаем список товаров
}

// Загружаем товары при запуске
tg.ready();
loadProducts();