from typing import Any, Union
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol
import string
import random
from messages import serialize, deserialize

WebSocket = Union[WebSocketServerProtocol, WebSocketClientProtocol]


async def next_event(ws: WebSocket):
    return deserialize(await anext(aiter(ws)))


async def receive_events(ws: WebSocket):
    async for msg in ws:
        yield deserialize(msg)


async def send_event(ws: WebSocket, data: Any):
    await ws.send(serialize(data))


def rand_num_str(n):
    return "".join(random.sample(string.digits, n))
