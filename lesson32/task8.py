from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Product API",
    description="An API used to demonstrate automatically generated FastAPI documentation.",
    version="1.0.0",
)


class Product(BaseModel):
    name: str
    price: float


@app.get("/products", tags=["Products"])
async def list_products():
    """Return all products. Example: `GET /products`."""
    return []


@app.post("/products", tags=["Products"])
async def create_product(product: Product):
    """Create one product from a JSON request body."""
    return product
