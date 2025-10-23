import websocket
import time

WS_URL = "ws://127.0.0.1:8000/ws/status/38873155-51be-460c-8f4b-2e0f119d22b6"

print(f"CLIENT: Connecting to {WS_URL}...")

try:
    # 1. Create the connection
    ws = websocket.create_connection(WS_URL)
    print("CLIENT: Connected!")

    # 2. Listen for messages in a loop
    #    The 'ws.recv()' part will WAIT (block)
    #    until the server sends something.
    while True:
        message = ws.recv() # This line waits...
        
        print("\nCLIENT: Server PUSHED a message!")
        print(f">>> {message}")
        
except websocket._exceptions.WebSocketConnectionClosedException:
    print("\nCLIENT: Server closed the connection. Demo complete.")
except ConnectionRefusedError:
    print("\nCLIENT: Error! Could not connect. Is the server running?")
except Exception as e:
    print(f"An error occurred: {e}")