# app/models.py
from sqlalchemy import Integer, String, select
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
from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_product(request: web.Request) -> web.Response:
    try:
        product_id = int(request.match_info["id"])
    except ValueError as error:
        raise web.HTTPBadRequest(text="ID produktu musi być liczbą") from error

    session_factory: async_sessionmaker[AsyncSession] = request.app["db_session_factory"]
    async with session_factory() as session:
        product = await session.scalar(
            select(Product).where(Product.id == product_id)
        )
    if product is None:
        raise web.HTTPNotFound()
    return web.json_response(product.to_dict())


# app/routes.py
def setup_routes(app: web.Application) -> None:
    app.router.add_get("/products/{id}", get_product)
