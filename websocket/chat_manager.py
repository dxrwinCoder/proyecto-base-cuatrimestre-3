from fastapi import WebSocket
from typing import Dict, List, Tuple


class ConnectionManager:
    def __init__(self):
        # { conversation_key: [WebSocket] } where key = frozenset({user1, user2})
        self.active_connections: Dict[frozenset, List[WebSocket]] = {}
        # presencia: {user_id: {"status": "online"/"offline", "count": n}}
        self.online: Dict[int, Dict[str, int]] = {}

    async def connect(self, websocket: WebSocket, user_a: int, user_b: int):
        await websocket.accept()
        key = frozenset({user_a, user_b})
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append(websocket)
        self._mark_online(user_a)
        self._mark_online(user_b)
        return key

    def disconnect(self, websocket: WebSocket, key: frozenset):
        if key in self.active_connections:
            self.active_connections[key].remove(websocket)
            if not self.active_connections[key]:
                del self.active_connections[key]
        # No sabemos qué usuario es, pero podemos limpiar counts si es el último ws del usuario
        # La limpieza fina se hace desde chat.py al salir

    def _mark_online(self, user_id: int):
        entry = self.online.get(user_id, {"status": "offline", "count": 0})
        entry["count"] = entry.get("count", 0) + 1
        entry["status"] = "online"
        self.online[user_id] = entry

    def mark_offline(self, user_id: int):
        entry = self.online.get(user_id)
        if not entry:
            return
        entry["count"] = max(entry.get("count", 1) - 1, 0)
        if entry["count"] == 0:
            entry["status"] = "offline"
        self.online[user_id] = entry

    async def send_to_conversation(self, message: dict, key: frozenset):
        if key in self.active_connections:
            for connection in self.active_connections[key]:
                await connection.send_json(message)


manager = ConnectionManager()
