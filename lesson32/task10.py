# app/dependencies.py
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

API_KEY = "lesson33-demo-key"


async def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> str:
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key


# app/main.py
app = FastAPI()


@app.get("/protected/books", dependencies=[Depends(verify_api_key)])
async def protected_books():
    return {"message": "Books access granted"}


@app.get("/protected/authors", dependencies=[Depends(verify_api_key)])
async def protected_authors():
    return {"message": "Authors access granted"}


@app.get("/protected/reports", dependencies=[Depends(verify_api_key)])
async def protected_reports():
    return {"message": "Reports access granted"}
