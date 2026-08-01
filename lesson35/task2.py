import argparse

import psutil
from aiohttp import web


async def health(request):
    memory = psutil.virtual_memory()
    return web.json_response(
        {
            "status": "ok",
            "memory_percent": memory.percent,
            "memory_available_bytes": memory.available,
        },
        status=200,
    )


def create_app():
    app = web.Application()
    app.router.add_get("/health", health)
    return app


def main():
    parser = argparse.ArgumentParser(description="Uruchamia endpoint /health.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    web.run_app(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
