const tg = window.Telegram.WebApp;

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
            <span>${item.quantity} x ${item.price} ₽</span>
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


// Открытие формы оформления заказа
document.getElementById('checkout-button').addEventListener('click', () => {
    document.getElementById('cart-modal').style.display = 'none';
    document.getElementById('checkout-modal').style.display = 'flex';

    // Автозаполнение данных из Telegram
    const user = tg.initDataUnsafe.user;
    if (user) {
        document.getElementById('name').value = user.first_name || '';
        document.getElementById('phone').value = user.phone_number || '';
    }
});


// Закрытие формы оформления заказа
document.getElementById('close-checkout-button').addEventListener('click', () => {
    document.getElementById('checkout-modal').style.display = 'none';
});


// Отправка формы
document.getElementById('checkout-form').addEventListener('submit', (event) => {
    event.preventDefault();

    const name = document.getElementById('name').value;
    const phone = document.getElementById('phone').value;

    // Формируем сообщение для отправки
    let message = `Новый заказ!\n\n`;
    message += `Имя: ${name}\n`;
    message += `Телефон: ${phone}\n\n`;
    message += `Товары:\n`;

    cartItems.forEach(item => {
        message += `${item.name} - ${item.quantity} x ₽${item.price}\n`;
    });

    message += `\nИтого: ₽${cartItems.reduce((total, item) => total + item.price * item.quantity, 0).toFixed(2)}`;

    // Отправляем данные в Telegram
    tg.sendData(JSON.stringify({
        message: message,
        cartItems: cartItems,
        name: name,
        phone: phone
    }));

    // Закрываем форму
    document.getElementById('checkout-modal').style.display = 'none';

    // Очищаем корзину
    cartItems = [];
    updateCartUI();
});