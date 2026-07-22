# app/main.py
from aiohttp import web

from app.database import configured_db_url, database_context
from app.routes import setup_routes


def create_app() -> web.Application:
    app = web.Application()
    app["db_url"] = configured_db_url()
    app.cleanup_ctx.append(database_context)
    setup_routes(app)
    return app


# app/routes.py
from app import handlers


def setup_routes(app: web.Application) -> None:
    app.router.add_get("/", handlers.handle_index)
    app.router.add_get("/witaj/{imie}", handlers.handle_welcome)
    app.router.add_get("/api/status", handlers.handle_status)
    app.router.add_get("/api/search", handlers.handle_search)
    app.router.add_post("/api/echo", handlers.handle_echo)
    app.router.add_post("/api/v1/chat", handlers.chat)
    app.router.add_post("/users", handlers.create_user)
    app.router.add_get("/users", handlers.get_users)
    app.router.add_post("/products", handlers.create_product)
    app.router.add_get("/products", handlers.get_products)
    app.router.add_get("/products/{id}", handlers.get_product)
    app.router.add_put("/products/{id}", handlers.update_product)
    app.router.add_delete("/products/{id}", handlers.delete_product)
    app.router.add_post("/transfer", handlers.transfer)
