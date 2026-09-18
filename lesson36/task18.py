APP = r'''
import asyncio
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CHANNEL = "chat"
app = FastAPI()

@app.websocket("/ws")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHANNEL)

    async def receive_client():
        while True:
            message = await ws.receive_text()
            await redis.publish(CHANNEL, message)

    async def send_messages():
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await ws.send_text(message["data"])
            await asyncio.sleep(0.01)

    tasks = [asyncio.create_task(receive_client()), asyncio.create_task(send_messages())]
    try:
        await asyncio.gather(*tasks)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.aclose()
        await redis.aclose()
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn redis
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

NGINX_CONFIG = r'''
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

upstream chat_backends {
    zone chat_backends 64k;
    resolver 127.0.0.11 valid=5s ipv6=off;
    server backend:8000 resolve;
}

server {
    listen 80;
    location /ws {
        proxy_pass http://chat_backends;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
    }
}
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
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; s=socket.create_connection(('127.0.0.1', 8000), 2); s.close()"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 2s
      retries: 10

  nginx:
    image: nginx:alpine
    ports:
      - "127.0.0.1:8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      backend:
        condition: service_healthy
'''

COMMANDS = r'''
docker compose up --build -d --scale backend=3
# Connect multiple WebSocket clients to ws://localhost:8080/ws and verify messages propagate through Redis Pub/Sub.
'''
