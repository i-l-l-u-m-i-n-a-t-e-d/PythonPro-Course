APP = r'''
import asyncio
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.asyncio import Redis

redis = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
FAKE_DATABASE = {"message": "value from database"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await redis.aclose()

app = FastAPI(lifespan=lifespan)

@app.get("/data")
async def get_data():
    cached = await redis.get("demo:data")
    if cached:
        return {"source": "cache", "data": json.loads(cached)}
    await asyncio.sleep(1)
    data = FAKE_DATABASE
    await redis.set("demo:data", json.dumps(data), ex=60)
    return {"source": "database", "data": data}
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn redis
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

COMPOSE = r'''
services:
  backend:
    build: ./backend
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 2s
      retries: 10
'''

COMMANDS = r'''
docker compose up --build --wait
curl http://localhost:8000/data
curl http://localhost:8000/data
'''
