from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

# This class manages all active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any message from the client
            data = await websocket.receive_text()
            # Broadcast that message to all connected clients
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)