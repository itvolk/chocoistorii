FROM python:3.9-slim

# Запрещаем автоматический перезапуск
STOPSIGNAL SIGINT

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Сначала копируем только requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости (с очисткой кэша)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Затем копируем остальные файлы
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

CMD ["python", "telegram_bot.py"]