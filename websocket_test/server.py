import asyncio
import websockets

async def echo(websocket, path):
    async for message in websocket:
        print(f"Received message from client: {message}")
        await websocket.send(f"Server echoes: {message}")

async def main():
    server = await websockets.serve(echo, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")
    await server.wait_closed()

asyncio.run(main())
