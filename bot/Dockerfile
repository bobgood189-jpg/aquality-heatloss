FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Persist the SQLite DB on a mounted volume in production:
#   docker run -e BOT_TOKEN=... -e OWNER_ID=... -e DB_PATH=/data/bot.db -v aq_data:/data ...
CMD ["python", "-m", "app.bot"]
