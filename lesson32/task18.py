# app/models.py
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Float, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)


# app/database.py
engine = create_async_engine("sqlite+aiosqlite:///./books.db")
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# app/schemas.py
class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: float
    category: str


# app/routers/books.py
app = FastAPI()


@app.get("/books", response_model=list[BookResponse])
async def list_books(
    session: AsyncSession = Depends(get_session),
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    sort_by: Literal["price", "title"] = "title",
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price cannot exceed max_price")
    statement = select(Book)
    if category is not None:
        statement = statement.where(Book.category == category)
    if min_price is not None:
        statement = statement.where(Book.price >= min_price)
    if max_price is not None:
        statement = statement.where(Book.price <= max_price)
    order_column = {"price": Book.price, "title": Book.title}[sort_by]
    statement = statement.order_by(order_column, Book.id).offset(skip).limit(limit)
    return list((await session.scalars(statement)).all())
