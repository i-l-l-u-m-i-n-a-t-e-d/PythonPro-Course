APP = r'''
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import psycopg
from psycopg.rows import dict_row

DB = os.environ["DATABASE_URL"]
REQUESTS = Counter("books_requests_total", "Requests to the books API", ["method"])

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

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/books")
def list_books():
    REQUESTS.labels("GET").inc()
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        return conn.execute("SELECT id, title, author FROM books ORDER BY id").fetchall()

@app.post("/books", status_code=status.HTTP_201_CREATED)
def create_book(book: BookIn):
    REQUESTS.labels("POST").inc()
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        row = conn.execute("INSERT INTO books(title, author) VALUES (%s, %s) RETURNING id, title, author", (book.title, book.author)).fetchone()
        conn.commit()
        return row

@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookIn):
    REQUESTS.labels("PUT").inc()
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        row = conn.execute("UPDATE books SET title=%s, author=%s WHERE id=%s RETURNING id, title, author", (book.title, book.author, book_id)).fetchone()
        conn.commit()
        if row is None:
            raise HTTPException(404, "Book not found")
        return row

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    REQUESTS.labels("DELETE").inc()
    with psycopg.connect(DB) as conn:
        cur = conn.execute("DELETE FROM books WHERE id=%s", (book_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "Book not found")
    return Response(status_code=204)
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn "psycopg[binary]" prometheus-client
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

PROMETHEUS_CONFIG = r'''
global:
  scrape_interval: 5s
scrape_configs:
  - job_name: backend
    static_configs:
      - targets: ["backend:8000"]
'''

GRAFANA_DATASOURCE = r'''
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
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
    ports:
      - "127.0.0.1:8000:8000"

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

  prometheus:
    image: prom/prometheus:latest
    command: ["--config.file=/etc/prometheus/prometheus.yml"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "127.0.0.1:9090:9090"
    depends_on:
      - backend

  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./grafana-datasource.yml:/etc/grafana/provisioning/datasources/datasource.yml:ro
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      - prometheus

volumes:
  postgres-data:
'''
