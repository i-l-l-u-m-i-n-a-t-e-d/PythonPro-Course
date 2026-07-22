from aiohttp import web


async def handle_index(request: web.Request) -> web.Response:
    return web.Response(text="<h1>Witaj na mojej stronie!</h1>", content_type="text/html")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8080)
