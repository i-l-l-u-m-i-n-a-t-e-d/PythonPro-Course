import json

from aiohttp import ContentTypeError, web


async def handle_echo(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except (json.JSONDecodeError, ValueError, ContentTypeError) as error:
        raise web.HTTPBadRequest(text="Oczekiwano poprawnego JSON-a") from error
    return web.json_response(data)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/api/echo", handle_echo)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8080)
