import json
from typing import Any, Union
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol

WebSocket = Union[WebSocketServerProtocol, WebSocketClientProtocol]


async def receive_events(ws: WebSocket):
    async for msg in ws:
        x = json.loads(msg)
        yield x["type"], x["data"]


async def send_event(ws: WebSocket, type: str, data: Any):
    await ws.send(json.dumps({"type": type, "data": data}))
