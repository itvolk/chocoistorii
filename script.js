const tg = window.Telegram.WebApp;

let cartItems = [];

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

function addToCart(button) {
    const productCard = button.closest('.product-card');
    const product = {
        name: productCard.querySelector('h3').innerText,
        price: parseFloat(productCard.querySelector('.price').innerText),
        quantity: parseInt(productCard.querySelector('.quantity-input').value)
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
    let total = 0;

    cartItemsContainer.innerHTML = '';
    
    cartItems.forEach((item, index) => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;

        const itemElement = document.createElement('div');
        itemElement.className = 'cart-item';
        itemElement.innerHTML = `
            <span>${item.name}</span>
            <span>${item.quantity} x $${item.price}</span>
            <button class="remove-item" onclick="removeFromCart(${index})">×</button>
        `;
        cartItemsContainer.appendChild(itemElement);
    });

    totalElement.textContent = total.toFixed(2);
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
            <button class="remove-item" onclick="removeFromCart(${index})">Х</button>
        `;
        cartItemsContainer.appendChild(itemElement);
    });

    totalElement.textContent = total.toFixed(2);

    // Обновляем стиль кнопки корзины
    if (cartItems.length > 0) {
        cartButton.classList.add('has-items'); // Добавляем класс, если есть товары
    } else {
        cartButton.classList.remove('has-items'); // Убираем класс, если корзина пуста
    }
}

function sendCartData() {
    const cartData = JSON.stringify(cartItems);
    tg.sendData(cartData);
}

document.getElementById('checkout-button').addEventListener('click', sendCartData);

// Инициализация Telegram Web App
tg.MainButton.show();
tg.MainButton.setText("Закрыть");
tg.MainButton.onClick(() => {
    tg.close();
});