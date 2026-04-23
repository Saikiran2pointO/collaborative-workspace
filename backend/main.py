from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Announce the new user count to everyone
        await self.broadcast_system_state()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_system_state(self):
        # Create a JSON payload with the user count
        payload = {"type": "system", "active_users": len(self.active_connections)}
        message = json.dumps(payload)
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_code(self, code: str):
        # Wrap the raw code in a JSON payload
        payload = {"type": "code", "content": code}
        message = json.dumps(payload)
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We receive raw text from the client's editor...
            data = await websocket.receive_text()
            # ...and broadcast it properly packaged as code
            await manager.broadcast_code(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # If someone closes their tab, update the user count for everyone else
        await manager.broadcast_system_state()