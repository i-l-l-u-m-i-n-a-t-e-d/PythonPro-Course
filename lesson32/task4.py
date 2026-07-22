from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class Product(BaseModel):
    name: str
    price: float = Field(gt=0)
    quantity: int = Field(ge=0)


@app.post("/products")
async def create_product(product: Product):
    return {**product.model_dump(), "total_price": product.price * product.quantity}
