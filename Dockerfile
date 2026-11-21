FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copies the app code AND the SQLite database (instance/events.db).
# .dockerignore deliberately does not exclude instance/ or *.db.
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
