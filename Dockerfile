# Dockerfile

# Шаг 1: Базовый образ (не меняется)
FROM python:3.11-slim
ENV PYTHONUNBUFFERED 1

# Шаг 2: Установка системных зависимостей (меняется редко)
# Этот слой будет надежно кэширован.
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Шаг 3: Установка зависимостей Python (меняется только при обновлении requirements.txt)
# Копируем только requirements.txt, чтобы слой с pip install не инвалидировался
# при каждом изменении кода.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Шаг 4: Настройка cron (меняется редко)
# Копируем файл cronjob до основного кода.
COPY cronjob /etc/cron.d/app-cron
RUN chmod 0644 /etc/cron.d/app-cron
# Создаем лог-файл, чтобы cron мог в него писать
RUN touch /var/log/cron.log

# Шаг 5: Копирование кода приложения (меняется чаще всего)
# Этот слой будет инвалидироваться при каждом изменении кода, но все, что было "до",
# останется в кэше.
COPY . .

# Шаг 6: Запуск cron
CMD cron -f