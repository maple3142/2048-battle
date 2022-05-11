import json
from typing import Any, Union
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol
import string
import random

WebSocket = Union[WebSocketServerProtocol, WebSocketClientProtocol]


def parse_msg(msg):
    x = json.loads(msg)
    return x["type"], x["data"]


async def next_event(ws: WebSocket):
    return parse_msg(await anext(aiter(ws)))


async def receive_events(ws: WebSocket):
    async for msg in ws:
        yield parse_msg(msg)


async def send_event(ws: WebSocket, type: str, data: Any = None):
    await ws.send(json.dumps({"type": type, "data": data}))


def rand_num_str(n):
    return "".join(random.sample(string.digits, n))
