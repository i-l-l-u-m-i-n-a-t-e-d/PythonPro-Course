# app/models.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "name": self.name, "price": self.price}


# app/database.py
import os

from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


async def init_db(app: web.Application) -> None:
    db_url = os.environ.get("DB_URL", "sqlite+aiosqlite:///./lesson32.db")
    engine = create_async_engine(db_url)
    app["db_engine"] = engine
    app["db_session_factory"] = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db(app: web.Application) -> None:
    await app["db_engine"].dispose()


# app/handlers.py
from typing import Any


async def create_product(request: web.Request) -> web.Response:
    try:
        data: dict[str, Any] = await request.json()
        name = data["name"]
        price = data["price"]
    except (KeyError, ValueError) as error:
        raise web.HTTPBadRequest(text="Wymagane są pola name i price w JSON-ie") from error
    if not isinstance(name, str) or not name.strip() or not isinstance(price, int):
        raise web.HTTPBadRequest(text="Niepoprawne dane produktu")

    session_factory: async_sessionmaker[AsyncSession] = request.app["db_session_factory"]
    async with session_factory() as session:
        async with session.begin():
            product = Product(name=name.strip(), price=price)
            session.add(product)
            await session.flush()
            product_data = product.to_dict()
    return web.json_response(product_data, status=201)


# app/routes.py
def setup_routes(app: web.Application) -> None:
    app.router.add_post("/products", create_product)
