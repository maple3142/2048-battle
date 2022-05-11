import asyncio
import argparse
from websockets.server import serve, WebSocketServerProtocol
from shared_utils import receive_events, send_event


async def handler(ws: WebSocketServerProtocol):
    async for type, data in receive_events(ws):
        print(type, data)
        await send_event(ws, type, data)


async def start(host, port):
    async with serve(handler, host, port):
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Game server")
    parser.add_argument("--port", type=int, default=1357, help="Server port")
    parser.add_argument("--host", type=str, default="localhost", help="Server host")
    args = parser.parse_args()
    asyncio.run(start(args.host, args.port))
