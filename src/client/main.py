import asyncio
from websockets.client import connect
from shared_utils import receive_events, send_event

async def hello():
    async with connect("ws://localhost:1357") as ws:
        await send_event(ws, 'test',{'a':1,'b':2})
        async for type, data in receive_events(ws):
            print(type, data)

if __name__ == "__main__":
    asyncio.run(hello())
