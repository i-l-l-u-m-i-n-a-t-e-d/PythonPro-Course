APP = r'''
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]

class BookIn(BaseModel):
    title: str
    author: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS books (id SERIAL PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL)")
        conn.commit()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/books")
def list_books():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        return conn.execute("SELECT id, title, author FROM books ORDER BY id").fetchall()

@app.post("/books", status_code=status.HTTP_201_CREATED)
def create_book(book: BookIn):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        row = conn.execute(
            "INSERT INTO books (title, author) VALUES (%s, %s) RETURNING id, title, author",
            (book.title, book.author),
        ).fetchone()
        conn.commit()
        return row

@app.put("/books/{book_id}")
def update_book(book_id: int, book: BookIn):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        row = conn.execute(
            "UPDATE books SET title=%s, author=%s WHERE id=%s RETURNING id, title, author",
            (book.title, book.author, book_id),
        ).fetchone()
        conn.commit()
        if row is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return row

@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int):
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute("DELETE FROM books WHERE id=%s", (book_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Book not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn "psycopg[binary]"
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
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

volumes:
  postgres-data:
'''
