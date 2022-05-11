import json
from typing import Any, Union
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol
import string
import random

WebSocket = Union[WebSocketServerProtocol, WebSocketClientProtocol]


async def receive_events(ws: WebSocket):
    async for msg in ws:
        x = json.loads(msg)
        yield x["type"], x["data"]


async def send_event(ws: WebSocket, type: str, data: Any = None):
    await ws.send(json.dumps({"type": type, "data": data}))

def rand_num_str(n):
    return ''.join(random.sample(string.digits, n))
