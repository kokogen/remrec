# Dockerfile

# --- Этап 1: "Строитель" (Builder) ---
# На этом этапе мы устанавливаем все зависимости, включая системные.
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Устанавливаем системные зависимости, необходимые для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Создаем виртуальное окружение, чтобы не засорять системный Python
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем только requirements.txt и устанавливаем зависимости в venv
# Этот слой будет кэшироваться, если requirements.txt не изменился
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
WORKDIR /app
COPY . .


# --- Этап 2: Финальный образ ---
# Этот образ будет максимально легковесным и безопасным.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Устанавливаем только те системные зависимости, которые нужны для *запуска*
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя без root-прав
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

# Копируем виртуальное окружение со всеми зависимостями из "строителя"
COPY --from=builder /opt/venv /opt/venv

# Копируем код приложения из "строителя"
WORKDIR /app
COPY --from=builder /app .

# Настраиваем cron
COPY cronjob /etc/cron.d/app-cron
RUN chmod 0644 /etc/cron.d/app-cron
RUN touch /var/log/cron.log && chown appuser:appuser /var/log/cron.log

# Устанавливаем правильного владельца для всех файлов приложения
RUN chown -R appuser:appuser /app

# Переключаемся на пользователя без root-прав
USER appuser

# Устанавливаем PATH, чтобы использовать Python из нашего venv
ENV PATH="/opt/venv/bin:$PATH"

# Запускаем cron от имени нового пользователя
CMD ["cron", "-f"]
