from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from typing import Dict
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        # Dictionary to store {websocket_object: "Username"}
        self.active_connections: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        # Save the connection with the user's name
        self.active_connections[websocket] = username
        await self.broadcast_system_state()

    def disconnect(self, websocket: WebSocket):
        # Remove the user when they leave
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    async def broadcast_system_state(self):
        # Get a list of all current usernames
        users = list(self.active_connections.values())
        # Send both the count AND the list of names
        payload = {"type": "system", "users": users, "count": len(users)}
        message = json.dumps(payload)
        
        for connection in self.active_connections.keys():
            await connection.send_text(message)

    async def broadcast_code(self, code: str):
        payload = {"type": "code", "content": code}
        message = json.dumps(payload)
        for connection in self.active_connections.keys():
            await connection.send_text(message)

manager = ConnectionManager()

# Notice the new 'username' parameter here!
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, username: str = Query("Anonymous")):
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast_code(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast_system_state()