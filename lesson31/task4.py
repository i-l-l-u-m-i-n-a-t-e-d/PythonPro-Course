from datetime import datetime

from aiohttp import web


async def handle_status(request: web.Request) -> web.Response:
    return web.json_response(
        {"status": "OK", "server_time": datetime.now().isoformat()}
    )


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/status", handle_status)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8080)
