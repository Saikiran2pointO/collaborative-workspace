from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from typing import Dict
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        # NEW STRUCTURE: { "room_code": { websocket: "username" } }
        self.rooms: Dict[str, Dict[WebSocket, str]] = {}

    async def connect(self, websocket: WebSocket, room_code: str, username: str):
        await websocket.accept()
        
        # If the room doesn't exist yet, create it
        if room_code not in self.rooms:
            self.rooms[room_code] = {}
            
        # Add the user to the specific room
        self.rooms[room_code][websocket] = username
        await self.broadcast_system_state(room_code)

    def disconnect(self, websocket: WebSocket, room_code: str):
        # Remove the user from the room
        if room_code in self.rooms and websocket in self.rooms[room_code]:
            del self.rooms[room_code][websocket]
            
            # Housekeeping: If the room is empty, delete it from memory to save server space
            if len(self.rooms[room_code]) == 0:
                del self.rooms[room_code]

    async def broadcast_system_state(self, room_code: str):
        if room_code in self.rooms:
            users = list(self.rooms[room_code].values())
            payload = {"type": "system", "users": users, "count": len(users)}
            message = json.dumps(payload)
            
            # ONLY send to people in this specific room
            for connection in self.rooms[room_code].keys():
                await connection.send_text(message)

    async def broadcast_code(self, code: str, room_code: str):
        if room_code in self.rooms:
            payload = {"type": "code", "content": code}
            message = json.dumps(payload)
            for connection in self.rooms[room_code].keys():
                await connection.send_text(message)

manager = ConnectionManager()

# NEW: The URL now requires both username AND room_code
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    username: str = Query("Anonymous"),
    room_code: str = Query(...)
):
    await manager.connect(websocket, room_code, username)
    try:
        while True:
            data = await websocket.receive_text()
            # Pass the room_code so it only broadcasts to the right room
            await manager.broadcast_code(data, room_code)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)
        # Update the user count for whoever is left in the room
        if room_code in manager.rooms:
            await manager.broadcast_system_state(room_code)