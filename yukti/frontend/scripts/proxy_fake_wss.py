import asyncio, ssl, websockets
async def echo(ws):
    async for m in ws:
        await ws.send("echo:" + m)
async def main():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain("cert.pem", "key.pem")
    async with websockets.serve(echo, "127.0.0.1", 18444, ssl=ctx):
        print("wss up", flush=True); await asyncio.Future()
asyncio.run(main())
