# app/database.py
from contextlib import asynccontextmanager
from pathlib import Path
import json
import os

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine("sqlite+aiosqlite:///./app.db")
CACHE_PATH = Path("cache.json")


class Base(DeclarativeBase):
    pass


async def initialize_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def load_cache() -> dict[str, object]:
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache: dict[str, object]) -> None:
    temporary = CACHE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, CACHE_PATH)


# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_database()
    app.state.cache = load_cache()
    try:
        yield
    finally:
        save_cache(app.state.cache)
        await engine.dispose()


app = FastAPI(lifespan=lifespan)
