import asyncio
import websockets

async def client():
    uri = "ws://localhost:8765"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                while True:
                    message = input("Enter message to send to server: ")
                    await websocket.send(message)
                    print(f"Sent message to server: {message}")

                    response = await websocket.recv()
                    print(f"Received response from server: {response}")
        except websockets.ConnectionClosedError:
            print("Connection closed, retrying in 30 seconds...")
            await asyncio.sleep(30)

asyncio.run(client())