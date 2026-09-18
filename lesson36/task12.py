DEV_COMPOSE = r'''
services:
  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: postgresql://app:demo_password@database:5432/app
    volumes:
      - ./backend:/app
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

PROD_COMPOSE = r'''
services:
  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
    environment:
      DATABASE_URL: postgresql://app:demo_password@database:5432/app
    depends_on:
      database:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"
    restart: unless-stopped

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
    restart: unless-stopped

volumes:
  postgres-data:
'''

COMMANDS = r'''
docker compose -f docker-compose.yml up --build --wait
docker compose -f docker-compose.yml down
docker compose -f docker-compose.prod.yml up --build --wait
docker compose -f docker-compose.prod.yml down
'''
