from fastapi import FastAPI, WebSocket
import asyncio

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # 1. Accept the connection
    await websocket.accept()
    print("SERVER: Client connected.")
    
    try:
        # 2. Send an immediate welcome message
        await websocket.send_text("You are connected! I will send a 'push' message in 5 seconds...")
        
        # 3. Simulate 5 seconds of work
        await asyncio.sleep(5)
        
        # 4. Push the final "answer" to the client
        print("SERVER: Work done, pushing message to client.")
        await websocket.send_text("🔥 Here is your delayed message! The server is pushing this. 🔥")
        
        # 5. Close the connection
        await websocket.close()
        print("SERVER: Client disconnected.")
        
    except Exception as e:
        # This catches errors if the client disconnects early
        print(f"SERVER: Client disconnected unexpectedly: {e}")