BACKEND_APP = r'''
import os
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel
import psycopg
from psycopg.rows import dict_row

DB = os.environ["DATABASE_URL"]

class BookIn(BaseModel):
    title: str
    author: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    with psycopg.connect(DB) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS books (id SERIAL PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL)")
        conn.commit()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/instance")
def instance():
    return {"backend": socket.gethostname()}

@app.get("/books")
def list_books():
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        return conn.execute("SELECT id, title, author FROM books ORDER BY id").fetchall()

@app.post("/books", status_code=status.HTTP_201_CREATED)
def create_book(book: BookIn):
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        row = conn.execute(
            "INSERT INTO books(title, author) VALUES (%s, %s) RETURNING id, title, author",
            (book.title, book.author),
        ).fetchone()
        conn.commit()
        return row

@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookIn):
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        row = conn.execute(
            "UPDATE books SET title=%s, author=%s WHERE id=%s RETURNING id, title, author",
            (book.title, book.author, book_id),
        ).fetchone()
        conn.commit()
        if row is None:
            raise HTTPException(404, "Book not found")
        return row

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    with psycopg.connect(DB) as conn:
        cur = conn.execute("DELETE FROM books WHERE id=%s", (book_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Book not found")
    return Response(status_code=204)
'''

BACKEND_DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn "psycopg[binary]"
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

NGINX_CONFIG = r'''
upstream backend_pool {
    zone backend_pool 64k;
    resolver 127.0.0.11 valid=5s ipv6=off;
    server backend:8000 resolve;
}

server {
    listen 80;

    location /static/ {
        alias /usr/share/nginx/html/static/;
    }

    location / {
        proxy_pass http://backend_pool;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
'''

STATIC_FILE = r'''
<!doctype html><html><body><h1>Static file served by Nginx</h1></body></html>
'''

COMPOSE = r'''
services:
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://app:demo_password@database:5432/app
    depends_on:
      database:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/books')"]
      interval: 5s
      timeout: 3s
      retries: 10

  database:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: demo_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - postgres-data:/var/lib/postgresql/data

  nginx:
    image: nginx:alpine
    ports:
      - "127.0.0.1:8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./static:/usr/share/nginx/html/static:ro
    depends_on:
      backend:
        condition: service_healthy

volumes:
  postgres-data:
'''

COMMANDS = r'''
docker compose up --build -d --scale backend=3
docker compose ps
for i in 1 2 3 4 5 6; do curl -s http://localhost:8080/instance; echo; done
curl -s http://localhost:8080/books
curl -s http://localhost:8080/static/index.html
'''
