const tg = window.Telegram.WebApp;

// Массив с данными товаров
const products = [
    {
        id: 1,
        name: "Помада",
        price: 150,
        image: "image/1.jpg",
    },
    {
        id: 2,
        name: "Корзинка",
        price: 700,
        image: "image/2.jpg",
    },
];

// Функция для создания карточки товара
function createProductCard(product) {
    return `
        <div class="product-card">
            <img src="${product.image}" class="product-image" alt="${product.name}">
            <h3>${product.name}</h3>
            <p>Цена: ₽ <span class="price">${product.price}</span></p>
            <button class="add-to-cart" onclick="addToCart(this)">В корзину</button>
        </div>
    `;
}

// Функция для отрисовки всех товаров
function renderProducts() {
    const container = document.querySelector('.container');
    container.innerHTML = ''; // Очищаем контейнер перед добавлением новых карточек

    products.forEach(product => {
        const productCard = createProductCard(product);
        container.insertAdjacentHTML('beforeend', productCard);
    });
}

// Логика корзины
let cartItems = [];

function addToCart(button) {
    const productCard = button.closest('.product-card');
    const product = {
        name: productCard.querySelector('h3').innerText,
        price: parseFloat(productCard.querySelector('.price').innerText),
        quantity: 1
    };

    const existingItem = cartItems.find(item => item.name === product.name);
    if (existingItem) {
        existingItem.quantity += product.quantity;
    } else {
        cartItems.push(product);
    }

    updateCartUI();
}

function removeFromCart(index) {
    cartItems.splice(index, 1);
    updateCartUI();
}

function updateCartUI() {
    const cartItemsContainer = document.getElementById('cart-items');
    const totalElement = document.getElementById('total');
    const cartButton = document.getElementById('open-cart-button');
    let total = 0;

    cartItemsContainer.innerHTML = '';
    
    cartItems.forEach((item, index) => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;

        const itemElement = document.createElement('div');
        itemElement.className = 'cart-item';
        itemElement.innerHTML = `
            <span>${item.name}</span>
            <span>${item.quantity} x ₽ ${item.price}</span>
            <button class="remove-item" onclick="removeFromCart(${index})">×</button>
        `;
        cartItemsContainer.appendChild(itemElement);
    });

    totalElement.textContent = total.toFixed(2);

    // Обновляем стиль кнопки корзины
    if (cartItems.length > 0) {
        cartButton.classList.add('has-items');
    } else {
        cartButton.classList.remove('has-items');
    }
}

function sendCartData() {
    const cartData = JSON.stringify(cartItems);
    tg.sendData(cartData);
}

// Открытие корзины
document.getElementById('open-cart-button').addEventListener('click', () => {
    document.getElementById('cart-modal').style.display = 'flex';
});

// Закрытие корзины
document.getElementById('close-cart-button').addEventListener('click', () => {
    document.getElementById('cart-modal').style.display = 'none';
});

// Закрытие корзины при клике вне окна
window.addEventListener('click', (event) => {
    const modal = document.getElementById('cart-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
});

// Оформление заказа
document.getElementById('checkout-button').addEventListener('click', sendCartData);

// Инициализация Telegram Web App
tg.MainButton.show();
tg.MainButton.setText("Закрыть");
tg.MainButton.onClick(() => {
    tg.close();
});

// Отрисовка товаров при загрузке страницы
document.addEventListener('DOMContentLoaded', renderProducts);