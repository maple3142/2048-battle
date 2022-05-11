import asyncio
import argparse
from websockets.server import serve, WebSocketServerProtocol
from shared_utils import receive_events, send_event, rand_num_str
from typing import Dict, Set, Any
import logging
import os

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)


class Room:
    def __init__(
        self, room_id: str, ws1: WebSocketServerProtocol, ws2: WebSocketServerProtocol
    ):
        self.room_id = room_id
        self.ws1 = ws1
        self.ws2 = ws2

    async def connected(self):
        for ws in [self.ws1, self.ws2]:
            await send_event(ws, "connected")

    def match(self, ws) -> bool:
        return ws == self.ws1 or ws == self.ws2

    def __repr__(self):
        return f"Room({self.room_id}, {self.ws1}, {self.ws2})"


class MainServer:
    def __init__(self):
        self.pending_rooms: Dict[str, WebSocketServerProtocol] = {}
        self.rooms: Set[Room] = set()

    def find_matching_room(self, ws: WebSocketServerProtocol) -> Room:
        for room in self.rooms:
            if room.match(ws):
                return room

    async def handle_new_room(self, ws: WebSocketServerProtocol, data: Any):
        room_id = rand_num_str(8)
        self.pending_rooms[room_id] = ws
        await send_event(ws, "new_room_id", {"id": room_id})

    async def handle_connect(self, ws: WebSocketServerProtocol, data: Any):
        room_id = data["room_id"]
        if room_id in self.pending_rooms:
            ws2 = self.pending_rooms.pop(room_id)
            r = Room(room_id, ws, ws2)
            self.rooms.add(r)
            await r.connected()
            logging.info(f"new room created: {r}")
        else:
            await send_event(
                ws, "error", {"message": f"Unable to join room {room_id}."}
            )

    async def handle(self, ws: WebSocketServerProtocol):
        async for type, data in receive_events(ws):
            logging.info(f"received {type} message: {data}")
            handler = getattr(self, f"handle_{type}", None)
            if handler is not None:
                await handler(ws, data)


async def start(host, port):
    server = MainServer()
    async with serve(server.handle, host, port):
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Game server")
    parser.add_argument("--port", type=int, default=1357, help="Server port")
    parser.add_argument("--host", type=str, default="localhost", help="Server host")
    args = parser.parse_args()
    asyncio.run(start(args.host, args.port))
