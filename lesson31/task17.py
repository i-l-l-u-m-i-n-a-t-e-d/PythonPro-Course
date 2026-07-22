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


async def get_products(request: web.Request) -> web.Response:
    try:
        page = int(request.query.get("page", "1"))
        limit = int(request.query.get("limit", "10"))
    except ValueError as error:
        raise web.HTTPBadRequest(text="page i limit muszą być liczbami całkowitymi") from error
    if page <= 0 or limit <= 0:
        raise web.HTTPBadRequest(text="page i limit muszą być dodatnie")

    offset = (page - 1) * limit
    session_factory: async_sessionmaker[AsyncSession] = request.app["db_session_factory"]
    async with session_factory() as session:
        products = (
            await session.scalars(
                select(Product).order_by(Product.id).offset(offset).limit(limit)
            )
        ).all()
    return web.json_response([product.to_dict() for product in products])


# app/routes.py
def setup_routes(app: web.Application) -> None:
    app.router.add_get("/products", get_products)
