# app/middleware.py
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request

LOG_PATH = Path("requests.log")
app = FastAPI()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    request_id = str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - started
        with LOG_PATH.open("a", encoding="utf-8") as file:
            file.write(f"{request.method} {request.url.path} 500 {duration:.6f}s\n")
        raise
    duration = time.perf_counter() - started
    response.headers["X-Request-ID"] = request_id
    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(f"{request.method} {request.url.path} {response.status_code} {duration:.6f}s\n")
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}
