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


# app/handlers.py
from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def delete_product(request: web.Request) -> web.Response:
    try:
        product_id = int(request.match_info["id"])
    except ValueError as error:
        raise web.HTTPBadRequest(text="ID produktu musi być liczbą") from error

    session_factory: async_sessionmaker[AsyncSession] = request.app["db_session_factory"]
    async with session_factory() as session:
        async with session.begin():
            product = await session.get(Product, product_id)
            if product is None:
                raise web.HTTPNotFound()
            await session.delete(product)
    return web.Response(status=204)


# app/routes.py
def setup_routes(app: web.Application) -> None:
    app.router.add_delete("/products/{id}", delete_product)
