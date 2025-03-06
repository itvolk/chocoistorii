const express = require('express');
const multer = require('multer');
const app = express();
const port = 3000;

let products = [];

// Загрузка изображений
const upload = multer({ dest: 'uploads/' });

app.post('/upload', upload.single('file'), (req, res) => {
    const fileUrl = `https://your-api.com/uploads/${req.file.filename}`;
    res.json({ url: fileUrl });
});

// Добавление товара
app.post('/products', express.json(), (req, res) => {
    const product = req.body;
    products.push(product);
    res.status(201).send('Товар добавлен');
});

// Удаление товара
app.delete('/products/:id', (req, res) => {
    const productId = req.params.id;
    products = products.filter(product => product.id !== productId);
    res.status(200).send('Товар удален');
});

// Получение списка товаров
app.get('/products', (req, res) => {
    res.json(products);
});

app.listen(port, () => {
    console.log(`Сервер запущен на http://localhost:${port}`);
});