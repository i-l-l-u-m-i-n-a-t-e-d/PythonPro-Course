APP = r'''
import os
import psycopg
from aiohttp import web

DATABASE_URL = os.environ["DATABASE_URL"]

async def database_status(request):
    with psycopg.connect(DATABASE_URL) as conn:
        value = conn.execute("SELECT 1").fetchone()[0]
    return web.json_response({"database": "connected", "result": value})

app = web.Application()
app.router.add_get("/", database_status)
web.run_app(app, host="0.0.0.0", port=8000)
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir aiohttp "psycopg[binary]"
COPY main.py .
EXPOSE 8000
CMD ["python", "main.py"]
'''

COMPOSE = r'''
services:
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://app:demo_password@database:5432/app
    depends_on:
      - database
    ports:
      - "127.0.0.1:8000:8000"

  database:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: demo_password
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
'''

COMMANDS = r'''
docker compose up --build
'''
