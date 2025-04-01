// Инициализация Telegram WebApp
const tg = window.Telegram?.WebApp;
let cartItems = JSON.parse(localStorage.getItem('cart')) || [];

// Логирование инициализационных данных
console.log('Telegram WebApp init:', {
  version: tg?.version,
  platform: tg?.platform,
  initData: tg?.initData,
  initDataUnsafe: tg?.initDataUnsafe
});

// Безопасное получение элементов
const getElement = (id) => {
  const element = document.getElementById(id);
  if (!element) console.error(`Element #${id} not found!`);
  return element;
};

// Элементы интерфейса
const elements = {
  cartModal: getElement('cart-modal'),
  checkoutModal: getElement('checkout-modal'),
  cartItems: getElement('cart-items'),
  totalElement: getElement('total'),
  nameInput: getElement('name'),
  phoneInput: getElement('phone'),
  commentInput: getElement('comment'),
  openCartButton: getElement('open-cart-button'),
  closeCartButton: getElement('close-cart-button'),
  checkoutButton: getElement('checkout-button'),
  closeCheckoutButton: getElement('close-checkout-button'),
  checkoutForm: getElement('checkout-form')
};

// Глобальные функции для inline обработчиков
window.addToCart = function(button) {
  const productCard = button.closest('.product-card');
  if (!productCard) return;

  const priceElement = productCard.querySelector('.price');
  const nameElement = productCard.querySelector('h3');
  // Изменено: теперь ищем первое изображение в галерее
  const photoElement = productCard.querySelector('.gallery img');
  
  if (!priceElement || !nameElement) {
    console.error('Product card structure incorrect');
    return;
  }

  const product = {
    name: nameElement.textContent.trim(),
    price: parseFloat(priceElement.textContent.replace(/[^\d.]/g, '')),
    quantity: 1,
    // Используем абсолютный URL для фото
    photo_url: photoElement ? new URL(photoElement.src, window.location.href).href : null
  };

  if (!product.name || isNaN(product.price)) {
    console.error('Invalid product data:', product);
    return;
  }

  console.log('Adding product to cart:', product); // Логирование для отладки

  const existingItem = cartItems.find(item => item.name === product.name);
  if (existingItem) {
    existingItem.quantity++;
    // Обновляем фото, если оно изменилось
    if (product.photo_url) {
      existingItem.photo_url = product.photo_url;
    }
  } else {
    cartItems.push(product);
  }
  updateCart();
};

window.changeQuantity = function(index, delta) {
  if (!cartItems[index]) return;
  cartItems[index].quantity = Math.max(1, cartItems[index].quantity + delta);
  updateCart();
};

window.removeFromCart = function(index) {
  if (index >= 0 && index < cartItems.length) {
    cartItems.splice(index, 1);
    updateCart();
  }
};

// Обновление кнопки корзины
function updateCartButton() {
  if (elements.openCartButton) {
    elements.openCartButton.classList.toggle('has-items', cartItems.length > 0);
  }
}

// Обновление корзины
function updateCart() {
  localStorage.setItem('cart', JSON.stringify(cartItems));
  renderCart();
  updateCartButton();
  updateCartLayout();
}

// Отрисовка корзины
function renderCart() {
  if (!elements.cartItems || !elements.totalElement) return;

  elements.cartItems.innerHTML = '';
  let total = 0;

  cartItems.forEach((item, index) => {
    if (!item?.name || isNaN(item.price) || isNaN(item.quantity)) {
      console.warn('Invalid item removed:', item);
      cartItems.splice(index, 1);
      return;
    }

    const itemHTML = `
      <div class="cart-item">
        <span>${item.name}</span>
        <div class="item-controls">
          <button onclick="changeQuantity(${index}, -1)">-</button>
          <span>${item.quantity}</span>
          <button onclick="changeQuantity(${index}, 1)">+</button>
          
        </div>
        <span class="price">${(item.price * item.quantity).toFixed(2)} ₽</span>
        <button class="remove" onclick="removeFromCart(${index})"> ❌</button>
      </div>
    `;
    elements.cartItems.insertAdjacentHTML('beforeend', itemHTML);
    total += item.price * item.quantity;
  });

  elements.totalElement.textContent = total.toFixed(2);
  // Обновляем счетчик в кнопке корзины
  const cartCounter = document.getElementById('cart-counter');
  if (cartCounter) {
    const totalItems = cartItems.reduce((sum, item) => sum + item.quantity, 0);
    cartCounter.textContent = totalItems > 0 ? totalItems.toString() : '';
  }
}

// Управление модальными окнами
function openCart() {
  if (elements.cartModal) elements.cartModal.style.display = 'flex';
}

function closeModals() {
  if (elements.cartModal) elements.cartModal.style.display = 'none';
  if (elements.checkoutModal) elements.checkoutModal.style.display = 'none';
}

// Функция для показа уведомлений
function showAlert(message) {
  try {
    tg?.showAlert?.(message) || alert(message);
  } catch (e) {
    alert(message);
  }
}

// Обработчик отправки формы
function handleSubmit(e) {
  e.preventDefault();
  
  if (cartItems.length === 0) {
    showAlert('🛒 Корзина пуста!');
    return;
  }

  const name = elements.nameInput?.value.trim() || '';
  const phone = elements.phoneInput?.value.trim() || '';
  const comment = elements.commentInput?.value.trim() || '';
  
  if (!name) {
    showAlert('✏️ Введите ваше имя!');
    return;
  }
  
  if (!phone) {
    showAlert('📱 Введите номер телефона!');
    return;
  }

  const orderData = {
    cart_items: cartItems.map(item => ({
      name: item.name,
      price: item.price,
      quantity: item.quantity,
      photo_url: item.photo_url || null
    })),
    name: name,
    phone: phone,
    comment: comment,
    init_data: tg?.initDataUnsafe
  };

  console.log('Submitting order:', orderData);

  try {
    if (window.Telegram?.WebApp?.sendData) {
      Telegram.WebApp.sendData(JSON.stringify(orderData));
      showAlert('✅ Заказ успешно отправлен!');
      
      cartItems = [];
      localStorage.removeItem('cart');
      updateCart();
      closeModals();
      
      if (Telegram.WebApp.close) {
        setTimeout(() => Telegram.WebApp.close(), 1000);
      }
    } else {
      showAlert('✅ Заказ принят! Мы свяжемся с вами в ближайшее время.');
      console.log('Order data (for fallback):', orderData);
      
      cartItems = [];
      localStorage.removeItem('cart');
      updateCart();
      closeModals();
    }
  } catch (error) {
    console.error('Order submission error:', error);
    showAlert('❌ Ошибка при отправке заказа');
  }
}

// Функция для обновления состояния корзины
function updateCartLayout() {
    const body = document.body;
    const cartContainer = document.querySelector('.cart-button-container');
    const cartCounter = document.getElementById('cart-counter');
    
    // Проверяем, есть ли товары в корзине (примерная логика)
    const hasItems = cartCounter && cartCounter.textContent && parseInt(cartCounter.textContent) > 0;
    
    if (hasItems) {
        body.classList.add('has-cart-items');
        cartContainer.classList.add('has-items');
    } else {
        body.classList.remove('has-cart-items');
        cartContainer.classList.remove('has-items');
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
  // Привязка событий
  if (elements.openCartButton) {
    elements.openCartButton.addEventListener('click', openCart);
  }
  
  if (elements.closeCartButton) {
    elements.closeCartButton.addEventListener('click', closeModals);
  }
  
  if (elements.checkoutButton) {
    elements.checkoutButton.addEventListener('click', () => {
      closeModals();
      if (elements.checkoutModal) {
        elements.checkoutModal.style.display = 'flex';
      }
    });
  }
  
  if (elements.closeCheckoutButton) {
    elements.closeCheckoutButton.addEventListener('click', closeModals);
  }
  
  if (elements.checkoutForm) {
    elements.checkoutForm.addEventListener('submit', handleSubmit);
  }

  // Восстановление корзины
  cartItems = cartItems.filter(item => 
    item?.name && !isNaN(item.price) && !isNaN(item.quantity)
  );
  updateCart();
  
  // Инициализация Telegram WebApp
  if (tg) {
    tg.ready();
    tg.expand();
  }
});