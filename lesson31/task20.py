# app/models.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100))
    products: Mapped[list[Product]] = relationship(back_populates="creator")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    creator_id: Mapped[int | None] = mapped_column(
        ForeignKey("app_users.id"), nullable=True
    )
    creator: Mapped[User | None] = relationship(back_populates="products")

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
        result = await session.execute(
            select(Product, User)
            .join(User, Product.creator_id == User.id, isouter=True)
            .where(Product.id == product_id)
        )
        row = result.one_or_none()
    if row is None:
        raise web.HTTPNotFound()

    product, user = row
    product_data = product.to_dict()
    product_data["creator_username"] = user.username if user is not None else None
    return web.json_response(product_data)


# app/routes.py
def setup_routes(app: web.Application) -> None:
    app.router.add_get("/products/{id}", get_product)
