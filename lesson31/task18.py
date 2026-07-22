import asyncio
import json

from aiohttp import ContentTypeError, web


async def chat(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except (json.JSONDecodeError, ValueError, ContentTypeError) as error:
        raise web.HTTPBadRequest(text="Oczekiwano poprawnego JSON-a") from error
    prompt_text = data.get("prompt") if isinstance(data, dict) else None
    if not isinstance(prompt_text, str):
        raise web.HTTPBadRequest(text="Pole prompt musi być tekstem")

    await asyncio.sleep(3)
    return web.json_response(
        {"response": f"Otrzymałem twój prompt: '{prompt_text}' i przetworzyłem go."}
    )


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/api/v1/chat", chat)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8080)
