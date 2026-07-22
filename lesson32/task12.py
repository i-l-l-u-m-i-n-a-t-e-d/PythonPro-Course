import re

from fastapi import FastAPI
from pydantic import BaseModel, field_validator

app = FastAPI()


class Product(BaseModel):
    name: str
    price: float
    category: str

    @field_validator("name")
    @classmethod
    def name_is_alphanumeric(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9]+", value):
            raise ValueError("name must contain only letters and digits")
        return value

    @field_validator("price")
    @classmethod
    def price_is_in_range(cls, value: float) -> float:
        if not 0 < value <= 10_000:
            raise ValueError("price must be greater than 0 and at most 10000")
        return value

    @field_validator("category")
    @classmethod
    def category_is_allowed(cls, value: str) -> str:
        if value not in {"Electronics", "Books", "Clothing"}:
            raise ValueError("category must be Electronics, Books, or Clothing")
        return value


@app.post("/products")
async def create_product(product: Product):
    return product
