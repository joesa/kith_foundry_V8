FROM python:3.13-slim

WORKDIR /app

# Install system deps (needed by some Python packages, e.g. psycopg2-binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Use gunicorn with UvicornWorker; config from gunicorn_config.py
CMD ["gunicorn", "main:app", "-c", "gunicorn_config.py"]
