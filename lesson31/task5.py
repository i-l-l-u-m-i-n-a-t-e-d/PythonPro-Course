from aiohttp import web


async def handle_search(request: web.Request) -> web.Response:
    phrase = request.query.get("q")
    if phrase is None:
        return web.json_response({"błąd": "Brak parametru q"})
    return web.json_response({"szukana_fraza": phrase})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/search", handle_search)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8080)
