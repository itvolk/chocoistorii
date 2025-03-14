# Используем базовый образ Python 3.9
FROM python:3.9-slim

# Устанавливаем системные зависимости
RUN apt update && apt install -y gcc python3-dev

#
RUN pip install --upgrade pip


# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt
COPY requirements.txt .

# Очищаем кэш pip и устанавливаем зависимости
RUN pip cache purge
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install aiogram

# Копирование остальных файлов
COPY . .

# Запуск бота
CMD ["python", "telegram_bot.py"]

