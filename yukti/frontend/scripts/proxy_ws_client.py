import asyncio, websockets
async def main():
    async with websockets.connect("ws://127.0.0.1:3317/ws/live?session_id=t", open_timeout=5) as ws:
        await ws.send("ping"); print("WS_REPLY", await asyncio.wait_for(ws.recv(), 5))
asyncio.run(main())
