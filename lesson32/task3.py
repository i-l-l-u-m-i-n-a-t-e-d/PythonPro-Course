from typing import Literal

from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.get("/calculate")
async def calculate(
    a: int,
    b: int,
    operation: Literal["add", "subtract", "multiply", "divide"] = "add",
):
    if operation == "divide" and b == 0:
        raise HTTPException(status_code=400, detail="Cannot divide by zero")
    result = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b,
    }[operation]
    return {"result": result}
