BACKEND_APP = r'''
import os
from fastapi import FastAPI
from pydantic import BaseModel
from celery.result import AsyncResult
from tasks import celery_app, recommend_books

app = FastAPI()

class RecommendationRequest(BaseModel):
    query: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/recommendations", status_code=202)
def create_recommendation(request: RecommendationRequest):
    task = recommend_books.delay(request.query)
    return {"task_id": task.id}

@app.get("/jobs/{task_id}")
def job_status(task_id: str):
    task = AsyncResult(task_id, app=celery_app)
    return {"state": task.state, "result": task.result if task.successful() else None}
'''

CELERY_TASKS = r'''
import json
import math
import os
from celery import Celery
from openai import OpenAI
import psycopg
from psycopg.rows import dict_row
from redis import Redis

BROKER = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
DATABASE_URL = os.environ["DATABASE_URL"]
CACHE_URL = os.getenv("CACHE_URL", "redis://redis:6379/2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

celery_app = Celery("book_recommendations", broker=BROKER, backend=RESULT)

def embed(text):
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return client.embeddings.create(model=EMBEDDING_MODEL, input=text).data[0].embedding

def cosine(a, b):
    numerator = sum(x * y for x, y in zip(a, b))
    left = math.sqrt(sum(x * x for x in a))
    right = math.sqrt(sum(y * y for y in b))
    return numerator / (left * right) if left and right else 0.0

@celery_app.task
def recommend_books(query):
    cache = Redis.from_url(CACHE_URL, decode_responses=True)
    cache_key = f"recommend:{query.strip().lower()}"
    cached = cache.get(cache_key)
    if cached:
        return json.loads(cached)

    query_embedding = embed(query)
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS books (id SERIAL PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, embedding DOUBLE PRECISION[])")
        rows = conn.execute("SELECT id, title, description, embedding FROM books WHERE embedding IS NOT NULL").fetchall()

    ranked = sorted(
        ({"id": row["id"], "title": row["title"], "score": cosine(query_embedding, row["embedding"])} for row in rows),
        key=lambda item: item["score"],
        reverse=True,
    )[:5]
    cache.setex(cache_key, 300, json.dumps(ranked))
    return ranked
'''

SEED_SCRIPT = r'''
import os
from openai import OpenAI
import psycopg

books = [
    ("The Hobbit", "Fantasy adventure about Bilbo Baggins."),
    ("1984", "Dystopian novel about surveillance and authoritarianism."),
    ("Pride and Prejudice", "Romantic novel about Elizabeth Bennet and Mr Darcy."),
]
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS books (id SERIAL PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, embedding DOUBLE PRECISION[])")
    for title, description in books:
        vector = client.embeddings.create(model=model, input=description).data[0].embedding
        conn.execute("INSERT INTO books(title, description, embedding) VALUES (%s, %s, %s)", (title, description, vector))
    conn.commit()
'''

BACKEND_DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn celery redis openai "psycopg[binary]"
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''

FRONTEND_PACKAGE_JSON = r'''
{
  "scripts": {"build": "vite build"},
  "dependencies": {"vite": "latest", "vue": "latest"},
  "devDependencies": {}
}
'''

FRONTEND_INDEX = r'''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Book recommendations</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
'''

FRONTEND_MAIN_JS = r'''
import { createApp, ref } from 'vue'
import './style.css'

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

createApp({
  setup() {
    const query = ref('')
    const status = ref('')
    const results = ref([])

    async function recommend() {
      results.value = []
      status.value = 'Starting recommendation...'
      const response = await fetch('/api/recommendations', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: query.value})
      })
      const job = await response.json()

      for (let attempt = 0; attempt < 60; attempt++) {
        await sleep(1000)
        const jobResponse = await fetch(`/api/jobs/${job.task_id}`)
        const data = await jobResponse.json()
        status.value = data.state
        if (data.state === 'SUCCESS') {
          results.value = data.result || []
          return
        }
        if (data.state === 'FAILURE') return
      }
      status.value = 'TIMEOUT'
    }

    return {query, status, results, recommend}
  },
  template: `
    <main>
      <h1>Book recommendations</h1>
      <input v-model="query" placeholder="What do you want to read?">
      <button @click="recommend">Recommend</button>
      <p>{{ status }}</p>
      <ol><li v-for="book in results" :key="book.id">{{ book.title }}</li></ol>
    </main>`
}).mount('#app')
'''

FRONTEND_STYLE = r'''
body { font-family: sans-serif; max-width: 720px; margin: 3rem auto; padding: 0 1rem; }
input { width: 70%; padding: .6rem; }
button { padding: .6rem 1rem; margin-left: .5rem; }
'''

FRONTEND_DOCKERFILE = r'''
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
'''

FRONTEND_NGINX = r'''
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri /index.html;
    }
}
'''

COMPOSE = r'''
services:
  frontend:
    build: ./frontend
    ports:
      - "127.0.0.1:8080:80"
    depends_on:
      backend:
        condition: service_healthy

  backend:
    build: ./backend
    environment: &backend-env
      DATABASE_URL: postgresql://app:demo_password@database:5432/app
      CACHE_URL: redis://redis:6379/2
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      OPENAI_API_KEY: ${OPENAI_API_KEY:?Set OPENAI_API_KEY}
      EMBEDDING_MODEL: text-embedding-3-small
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 5s
      timeout: 3s
      retries: 10

  celery-worker:
    build: ./backend
    command: celery -A tasks:celery_app worker --loglevel=info
    environment: *backend-env
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy

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

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 2s
      retries: 10
    volumes:
      - redis-data:/data

volumes:
  postgres-data:
  redis-data:
'''

COMMANDS = r'''
export OPENAI_API_KEY="your_key_here"
docker compose up --build --wait
docker compose exec backend python seed.py
# frontend: http://localhost:8080
'''
