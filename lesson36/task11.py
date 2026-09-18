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

NGINX_CONFIG = r'''
upstream backend {
    server backend:8000;
}

server {
    listen 80;

    location /static/ {
        alias /usr/share/nginx/html/static/;
    }

    location / {
        proxy_pass http://backend;
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

COMMANDS = r'''
docker compose up --build --wait
curl http://localhost:8080/books
curl http://localhost:8080/static/index.html
'''
