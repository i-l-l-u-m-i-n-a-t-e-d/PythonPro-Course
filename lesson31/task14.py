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


# app/handlers.py
from typing import Any

from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def update_product(request: web.Request) -> web.Response:
    try:
        product_id = int(request.match_info["id"])
        data: dict[str, Any] = await request.json()
    except (ValueError, TypeError) as error:
        raise web.HTTPBadRequest(text="Niepoprawne ID lub JSON") from error
    if not isinstance(data, dict) or not ({"name", "price"} & data.keys()):
        raise web.HTTPBadRequest(text="Podaj name i/lub price")
    if "name" in data and (not isinstance(data["name"], str) or not data["name"].strip()):
        raise web.HTTPBadRequest(text="Pole name musi być niepustym tekstem")
    if "price" in data and (isinstance(data["price"], bool) or not isinstance(data["price"], int)):
        raise web.HTTPBadRequest(text="Pole price musi być liczbą całkowitą")

    session_factory: async_sessionmaker[AsyncSession] = request.app["db_session_factory"]
    async with session_factory() as session:
        async with session.begin():
            product = await session.get(Product, product_id)
            if product is None:
                raise web.HTTPNotFound()
            if "name" in data:
                product.name = data["name"].strip()
            if "price" in data:
                product.price = data["price"]
            await session.flush()
            product_data = product.to_dict()
    return web.json_response(product_data)


# app/routes.py
def setup_routes(app: web.Application) -> None:
    app.router.add_put("/products/{id}", update_product)
