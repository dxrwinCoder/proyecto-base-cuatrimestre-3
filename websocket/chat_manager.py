from fastapi import WebSocket
from typing import Dict, List, Tuple


class ConnectionManager:
    def __init__(self):
        # { conversation_key: [WebSocket] } where key = frozenset({user1, user2})
        self.active_connections: Dict[frozenset, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_a: int, user_b: int):
        await websocket.accept()
        key = frozenset({user_a, user_b})
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append(websocket)
        return key

    def disconnect(self, websocket: WebSocket, key: frozenset):
        if key in self.active_connections:
            self.active_connections[key].remove(websocket)
            if not self.active_connections[key]:
                del self.active_connections[key]

    async def send_to_conversation(self, message: dict, key: frozenset):
        if key in self.active_connections:
            for connection in self.active_connections[key]:
                await connection.send_json(message)


manager = ConnectionManager()
