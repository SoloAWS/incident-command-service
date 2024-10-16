FROM python:3.9-slim

WORKDIR /app

COPY . /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT 8004
EXPOSE $PORT

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"]