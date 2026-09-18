USERS_APP = r'''
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
import psycopg
from psycopg.rows import dict_row

DB = os.environ["DATABASE_URL"]
class UserIn(BaseModel):
    name: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    with psycopg.connect(DB) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT NOT NULL)")
        conn.commit()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/users")
def users():
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        return conn.execute("SELECT id, name FROM users ORDER BY id").fetchall()

@app.post("/users")
def create_user(user: UserIn):
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        row = conn.execute("INSERT INTO users(name) VALUES (%s) RETURNING id, name", (user.name,)).fetchone()
        conn.commit()
        return row
'''

POSTS_APP = r'''
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
import psycopg
from psycopg.rows import dict_row

DB = os.environ["DATABASE_URL"]
class PostIn(BaseModel):
    user_id: int
    title: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    with psycopg.connect(DB) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT NOT NULL)")
        conn.commit()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/posts")
def posts():
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        return conn.execute("SELECT id, user_id, title FROM posts ORDER BY id").fetchall()

@app.post("/posts")
def create_post(post: PostIn):
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        row = conn.execute("INSERT INTO posts(user_id, title) VALUES (%s, %s) RETURNING id, user_id, title", (post.user_id, post.title)).fetchone()
        conn.commit()
        return row
'''

GATEWAY_APP = r'''
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx
import psycopg

DB = os.environ["DATABASE_URL"]
USERS_URL = os.getenv("USERS_URL", "http://users-service:8000")
POSTS_URL = os.getenv("POSTS_URL", "http://posts-service:8000")

@asynccontextmanager
async def lifespan(app: FastAPI):
    with psycopg.connect(DB) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS gateway_requests (id SERIAL PRIMARY KEY, created_at TIMESTAMPTZ DEFAULT now())")
        conn.commit()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/feed")
async def feed():
    async with httpx.AsyncClient() as client:
        users, posts = await client.get(f"{USERS_URL}/users"), await client.get(f"{POSTS_URL}/posts")
    with psycopg.connect(DB) as conn:
        conn.execute("INSERT INTO gateway_requests DEFAULT VALUES")
        conn.commit()
    return {"users": users.json(), "posts": posts.json()}
'''

SERVICE_DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn httpx "psycopg[binary]"
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

COMPOSE = r'''
services:
  users-service:
    build: ./users-service
    environment:
      DATABASE_URL: postgresql://users:demo_password@users-db:5432/users
    depends_on:
      users-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/users')"]
      interval: 5s
      timeout: 3s
      retries: 10

  posts-service:
    build: ./posts-service
    environment:
      DATABASE_URL: postgresql://posts:demo_password@posts-db:5432/posts
    depends_on:
      posts-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/posts')"]
      interval: 5s
      timeout: 3s
      retries: 10

  api-gateway:
    build: ./api-gateway
    environment:
      DATABASE_URL: postgresql://gateway:demo_password@gateway-db:5432/gateway
      USERS_URL: http://users-service:8000
      POSTS_URL: http://posts-service:8000
    depends_on:
      gateway-db:
        condition: service_healthy
      users-service:
        condition: service_healthy
      posts-service:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"

  users-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: users
      POSTGRES_USER: users
      POSTGRES_PASSWORD: demo_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U users -d users"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - users-data:/var/lib/postgresql/data

  posts-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: posts
      POSTGRES_USER: posts
      POSTGRES_PASSWORD: demo_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U posts -d posts"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - posts-data:/var/lib/postgresql/data

  gateway-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: gateway
      POSTGRES_USER: gateway
      POSTGRES_PASSWORD: demo_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gateway -d gateway"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - gateway-data:/var/lib/postgresql/data

volumes:
  users-data:
  posts-data:
  gateway-data:
'''
