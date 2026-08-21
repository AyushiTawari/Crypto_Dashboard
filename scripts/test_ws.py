import asyncio
import websockets


async def main():
    uri = "ws://localhost:8000/ws/btcusdt"
    async with websockets.connect(uri) as ws:
        for _ in range(5):
            message = await ws.recv()
            print(message)


asyncio.run(main())