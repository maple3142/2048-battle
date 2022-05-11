import asyncio
from websockets.client import connect
from shared_utils import receive_events, send_event
import logging
import os

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)

async def hello():
    async with connect("ws://localhost:1357") as ws:
        await send_event(ws, "connect", {'room_id': '23098614'})
        async for type, data in receive_events(ws):
            logging.info((type, data))


if __name__ == "__main__":
    asyncio.run(hello())
