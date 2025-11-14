from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # { hogar_id: [WebSocket] }
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, hogar_id: int):
        await websocket.accept()
        if hogar_id not in self.active_connections:
            self.active_connections[hogar_id] = []
        self.active_connections[hogar_id].append(websocket)

    def disconnect(self, websocket: WebSocket, hogar_id: int):
        self.active_connections[hogar_id].remove(websocket)
        if not self.active_connections[hogar_id]:
            del self.active_connections[hogar_id]

    async def broadcast(self, message: dict, hogar_id: int):
        if hogar_id in self.active_connections:
            for connection in self.active_connections[hogar_id]:
                await connection.send_json(message)

manager = ConnectionManager()