# Dockerfile

# --- Stage 1: Builder ---
# In this stage, we install all dependencies, including system ones.
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to avoid polluting the system Python
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only requirements.txt and install dependencies into the venv
# This layer will be cached if requirements.txt has not changed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
WORKDIR /app
COPY . .


# --- Stage 2: Final Image ---
# This image will be as lightweight and secure as possible.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install only the system dependencies needed for *running* the application
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

# Copy the virtual environment with all dependencies from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code from the builder stage
WORKDIR /app
COPY --from=builder /app .

# Configure cron
COPY cronjob /etc/cron.d/app-cron
RUN chmod 0644 /etc/cron.d/app-cron
RUN touch /var/log/cron.log && chown appuser:appuser /var/log/cron.log

# Set the correct owner for all application files
RUN chown -R appuser:appuser /app


# Set the PATH to use Python from our venv
ENV PATH="/opt/venv/bin:$PATH"

# Run cron as the new user
CMD ["cron", "-f"]
