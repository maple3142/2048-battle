import asyncio
from websockets.client import connect, WebSocketClientProtocol
from messages import *
from shared_utils import receive_events, next_event, send_event
import logging
import os

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)


async def handle_ws1(ws: WebSocketClientProtocol):
    type, data = await next_event(ws)
    logging.info(("ws1", type, data))
    assert type == "connected"
    await asyncio.sleep(1)
    await send_event(ws, ClientUpdateMessage(123, 64))
    await asyncio.sleep(1)
    await send_event(ws, ClientUpdateMessage(8763, 512))
    await asyncio.sleep(2)
    await send_event(ws, ClientWinMessage(8763))
    async for type, data in receive_events(ws):
        logging.info(("ws1", type, data))
        if type == "disconnected":
            await ws.close()
            break


async def handle_ws2(ws: WebSocketClientProtocol):
    type, data = await next_event(ws)
    logging.info(("ws2", type, data))
    assert type == "connected"
    await asyncio.sleep(3)
    await send_event(ws, ClientUpdateMessage(3535, 256))
    async for type, data in receive_events(ws):
        logging.info(("ws2", type, data))
        if type == "opponent_win":
            await ws.close()
            break


async def main():
    async with connect("ws://localhost:1357") as ws1, connect(
        "ws://localhost:1357"
    ) as ws2:
        await send_event(ws1, NewRoomRequest())
        type, data = await anext(receive_events(ws1))
        logging.info((type, data))
        assert type == "new_room_id"
        await send_event(ws2, ConnectRequest(data.room_id))
        await asyncio.gather(handle_ws1(ws1), handle_ws2(ws2))


if __name__ == "__main__":
    asyncio.run(main())
