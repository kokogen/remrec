# Dockerfile
# Шаг 1: Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем переменную окружения, чтобы Python не буферизовал вывод
ENV PYTHONUNBUFFERED 1

# Шаг 2: Установка системных зависимостей
# - cron: планировщик задач
# - poppler-utils: необходим для библиотеки pdf2image для работы с PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Шаг 3: Установка рабочей директории внутри контейнера
WORKDIR /app

# Шаг 4: Копирование и установка зависимостей Python
# Копируем только requirements.txt, чтобы использовать кэш Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Шаг 5: Копирование всего кода приложения в рабочую директорию
COPY . .

# Шаг 6: Настройка cron
# Копируем файл с заданием cron в системную директорию cron
COPY cronjob /etc/cron.d/app-cron
# Устанавливаем правильные права доступа для файла cron
RUN chmod 0644 /etc/cron.d/app-cron
# Создаем пустой лог-файл, чтобы cron мог в него писать (хотя мы перенаправляем вывод)
RUN touch /var/log/cron.log

# Шаг 7: Запуск cron в качестве основного процесса контейнера
# `cron -f`: запускает cron в foreground-режиме, что необходимо для Docker
# `tail -f /var/log/cron.log`: показывает логи cron для отладки самого планировщика
CMD cron -f
