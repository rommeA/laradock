FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Копируем скрипт
COPY app.py .
COPY office.py .

# Запускаем скрипт
CMD ["python", "office.py"]
