# .private/tasks_15_20/task20.py
from __future__ import annotations

import asyncio
import json
from typing import Any

from aiohttp import WSMsgType, web


WINNING_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


class TicTacToeGame:
    def __init__(self) -> None:
        self.board: list[str | None] = [None] * 9
        self.players: dict[web.WebSocketResponse, str] = {}
        self.turn = "X"
        self.winner: str | None = None
        self.draw = False
        self._lock = asyncio.Lock()

    def _snapshot(self) -> dict[str, Any]:
        return {
            "type": "state",
            "board": list(self.board),
            "turn": self.turn if self.winner is None and not self.draw else None,
            "winner": self.winner,
            "draw": self.draw,
            "players": len(self.players),
        }

    def _reset_locked(self) -> None:
        self.board = [None] * 9
        self.turn = "X"
        self.winner = None
        self.draw = False

    async def _broadcast_state_locked(self) -> None:
        while True:
            stale: list[web.WebSocketResponse] = []
            snapshot = self._snapshot()
            for ws in tuple(self.players):
                if ws.closed:
                    stale.append(ws)
                    continue
                try:
                    await ws.send_json(snapshot)
                except Exception:
                    stale.append(ws)

            removed_player = False
            for ws in stale:
                if self.players.pop(ws, None) is not None:
                    removed_player = True
            if not removed_player:
                return

            # A player vanished while broadcasting. Reset and send a fresh,
            # authoritative state with the corrected player count.
            self._reset_locked()

    async def join(self, ws: web.WebSocketResponse) -> bool:
        async with self._lock:
            if len(self.players) >= 2:
                await ws.send_json({"type": "error", "message": "Gra jest pełna"})
                await ws.close()
                return False
            symbol = "X" if "X" not in self.players.values() else "O"
            self.players[ws] = symbol
            await ws.send_json({"type": "joined", "symbol": symbol})
            await self._broadcast_state_locked()
            return True

    async def leave(self, ws: web.WebSocketResponse) -> None:
        async with self._lock:
            if ws in self.players:
                self.players.pop(ws)
                self._reset_locked()
                await self._broadcast_state_locked()

    async def close(self) -> None:
        async with self._lock:
            sockets = tuple(self.players)
            self.players.clear()
            self._reset_locked()
        for socket in sockets:
            if not socket.closed:
                await socket.close()

    def _winner(self) -> str | None:
        for first, second, third in WINNING_LINES:
            symbol = self.board[first]
            if symbol and symbol == self.board[second] == self.board[third]:
                return symbol
        return None

    def _move_locked(self, ws: web.WebSocketResponse, position: int) -> str | None:
        symbol = self.players.get(ws)
        if symbol is None:
            return "Nie jesteś graczem"
        if len(self.players) != 2:
            return "Czekam na drugiego gracza"
        if self.winner is not None or self.draw:
            return "Gra została zakończona"
        if symbol != self.turn:
            return "To nie jest twoja kolej"
        if position < 0 or position > 8:
            return "Pozycja musi być od 0 do 8"
        if self.board[position] is not None:
            return "To pole jest zajęte"

        self.board[position] = symbol
        self.winner = self._winner()
        self.draw = self.winner is None and all(field is not None for field in self.board)
        if self.winner is None and not self.draw:
            self.turn = "O" if self.turn == "X" else "X"
        return None

    async def handle_move(self, ws: web.WebSocketResponse, position: int) -> None:
        async with self._lock:
            error = self._move_locked(ws, position)
            if error is not None:
                await ws.send_json({"type": "error", "message": error})
                return
            await self._broadcast_state_locked()


async def game_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    game: TicTacToeGame = request.app["game"]
    if not await game.join(ws):
        return ws

    try:
        async for message in ws:
            if message.type == WSMsgType.TEXT:
                try:
                    payload = json.loads(message.data)
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "message": "Niepoprawny JSON"})
                    continue
                if not isinstance(payload, dict):
                    await ws.send_json({"type": "error", "message": "Niepoprawny JSON"})
                    continue
                position = payload.get("position") if payload.get("type") == "move" else None
                if not isinstance(position, int) or isinstance(position, bool):
                    await ws.send_json({"type": "error", "message": "Podaj poprawny ruch"})
                    continue
                await game.handle_move(ws, position)
            elif message.type == WSMsgType.ERROR:
                break
    finally:
        await game.leave(ws)
    return ws


async def on_cleanup(app: web.Application) -> None:
    await app["game"].close()


def create_app() -> web.Application:
    app = web.Application()
    app["game"] = TicTacToeGame()
    app.router.add_get("/game", game_handler)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8080)

