const tg = window.Telegram.WebApp;

// Обработка отправки формы
document.getElementById('add-product-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('product-name').value;
    const price = document.getElementById('product-price').value;
    const imageFile = document.getElementById('product-image').files[0];

    // Загрузка изображения (если требуется)
    const imageUrl = await uploadImage(imageFile);

    // Отправка данных на сервер
    const response = await fetch('https://your-api.com/products', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name,
            price,
            image: imageUrl,
        }),
    });

    if (response.ok) {
        alert('Товар успешно добавлен!');
        tg.close(); // Закрываем мини-приложение
    } else {
        alert('Ошибка при добавлении товара');
    }
});

// Функция для загрузки изображения
async function uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('https://your-api.com/upload', {
        method: 'POST',
        body: formData,
    });

    const data = await response.json();
    return data.url; // Возвращаем URL загруженного изображения
}

tg.ready();