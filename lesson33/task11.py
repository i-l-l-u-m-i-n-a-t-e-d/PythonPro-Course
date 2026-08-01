# .private/tasks_8_14/task11.py
import asyncio
from collections import deque
from contextlib import suppress

from aiohttp import web


PING_INTERVAL = 30
PONG_TIMEOUT = 60


async def send_pings(
    ws: web.WebSocketResponse,
    outstanding_pings: deque[float],
    ping_interval: float,
) -> None:
    loop = asyncio.get_running_loop()
    next_ping_at = loop.time() + ping_interval
    while not ws.closed:
        await asyncio.sleep(max(0, next_ping_at - loop.time()))
        next_ping_at += ping_interval
        if ws.closed:
            return

        outstanding_pings.append(loop.time())
        try:
            await ws.send_str("ping")
        except (ConnectionResetError, RuntimeError):
            return


async def close_without_pong(
    ws: web.WebSocketResponse,
    outstanding_pings: deque[float],
    pong_timeout: float,
) -> None:
    loop = asyncio.get_running_loop()
    check_interval = min(1.0, pong_timeout / 10)
    while not ws.closed:
        await asyncio.sleep(check_interval)
        if outstanding_pings and loop.time() - outstanding_pings[0] >= pong_timeout:
            try:
                await ws.close(code=1008, message=b"Pong timeout")
            except ConnectionResetError:
                pass
            return


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    outstanding_pings: deque[float] = deque()
    ping_sender = asyncio.create_task(
        send_pings(
            ws,
            outstanding_pings,
            request.app["ping_interval"],
        )
    )
    timeout_monitor = asyncio.create_task(
        close_without_pong(ws, outstanding_pings, request.app["pong_timeout"])
    )

    try:
        async for message in ws:
            if message.type == web.WSMsgType.TEXT and message.data == "pong":
                if outstanding_pings:
                    outstanding_pings.popleft()
            elif message.type == web.WSMsgType.ERROR:
                break
    finally:
        for task in (ping_sender, timeout_monitor):
            task.cancel()
        for task in (ping_sender, timeout_monitor):
            with suppress(asyncio.CancelledError):
                await task

    return ws


def create_app(
    ping_interval: float = PING_INTERVAL, pong_timeout: float = PONG_TIMEOUT
) -> web.Application:
    app = web.Application()
    app["ping_interval"] = ping_interval
    app["pong_timeout"] = pong_timeout
    app.router.add_get("/ws", websocket_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
