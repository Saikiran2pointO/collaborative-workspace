from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Any
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, room_code: str, username: str, action: str):
        if room_code not in self.rooms:
            self.rooms[room_code] = {"host": username, "connections": {}}
        self.rooms[room_code]["connections"][websocket] = username
        await self.broadcast_system_state(room_code)

    def disconnect(self, websocket: WebSocket, room_code: str):
        if room_code in self.rooms and websocket in self.rooms[room_code]["connections"]:
            del self.rooms[room_code]["connections"][websocket]
            if len(self.rooms[room_code]["connections"]) == 0:
                del self.rooms[room_code]

    async def broadcast_system_state(self, room_code: str):
        if room_code in self.rooms:
            room_data = self.rooms[room_code]
            host_name = room_data["host"]
            users = []
            for uname in room_data["connections"].values():
                if uname == host_name:
                    users.append(f"{uname} (Host)")
                else:
                    users.append(uname)
            payload = {"type": "system", "users": users, "count": len(users)}
            message = json.dumps(payload)
            for connection in room_data["connections"].keys():
                await connection.send_text(message)

    async def broadcast_code(self, code: str, room_code: str):
        if room_code in self.rooms:
            payload = {"type": "code", "content": code}
            message = json.dumps(payload)
            for connection in self.rooms[room_code]["connections"].keys():
                await connection.send_text(message)

    # NEW: Broadcast typing status to everyone EXCEPT the person typing
    async def broadcast_typing(self, username: str, is_typing: bool, room_code: str, sender: WebSocket):
        if room_code in self.rooms:
            payload = {"type": "typing", "username": username, "typing": is_typing}
            message = json.dumps(payload)
            for connection in self.rooms[room_code]["connections"].keys():
                if connection != sender:
                    await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    username: str = Query(...),
    room_code: str = Query(...),
    action: str = Query(...) 
):
    await websocket.accept()

    if action == "join" and room_code not in manager.rooms:
        await websocket.send_text(json.dumps({"type": "error", "message": "Room does not exist. Please check your 6-digit code."}))
        await websocket.close()
        return

    if room_code in manager.rooms:
        existing_users = manager.rooms[room_code]["connections"].values()
        if username in existing_users:
            await websocket.send_text(json.dumps({"type": "error", "message": f"The name '{username}' is already taken in this room. Please choose another."}))
            await websocket.close()
            return

    await manager.connect(websocket, room_code, username, action)
    try:
        while True:
            # NEW: The server now expects JSON from the frontend
            data = await websocket.receive_text()
            try:
                parsed_data = json.loads(data)
                
                # Route the data based on what type of message it is
                if parsed_data["type"] == "code":
                    await manager.broadcast_code(parsed_data["content"], room_code)
                elif parsed_data["type"] == "typing":
                    await manager.broadcast_typing(username, parsed_data["typing"], room_code, websocket)
            
            except json.JSONDecodeError:
                pass # Ignore bad data
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)
        if room_code in manager.rooms:
            await manager.broadcast_system_state(room_code)