import asyncio
import websockets
import json

async def test_connection():
    try:
        print("Connecting to WebSocket...")
        async with websockets.connect('ws://localhost:8000/ws') as websocket:
            print("Connection established")
            
            # Send ping message
            ping_msg = json.dumps({"type": "ping"})
            print(f"Sending: {ping_msg}")
            await websocket.send(ping_msg)
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Keep connection open for a bit
            await asyncio.sleep(2)
            
            print("Test completed successfully")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_connection())
