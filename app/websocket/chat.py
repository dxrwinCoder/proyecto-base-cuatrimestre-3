from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from models.miembro import Miembro
from models.mensaje import Mensaje
from websocket.chat_manager import manager
from websocket.security import decode_jwt
from db.database import get_db
import json

async def get_miembro_from_token(token: str, db: AsyncSession):
    payload = decode_jwt(token)
    if not payload or "sub" not in payload:
        return None
    miembro_id = int(payload["sub"])
    miembro = await db.get(Miembro, miembro_id)
    return miembro if miembro and miembro.estado else None

async def chat_websocket(websocket: WebSocket, token: str):
    async for db in get_db():
        miembro = await get_miembro_from_token(token, db)
        if not miembro:
            await websocket.close(code=4001, reason="Token inválido")
            return

        hogar_id = miembro.id_hogar
        await manager.connect(websocket, hogar_id)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    body = json.loads(data)
                    contenido = body.get("contenido", "").strip()
                    if not contenido:
                        continue

                    nuevo_mensaje = Mensaje(
                        id_hogar=hogar_id,
                        id_remitente=miembro.id,
                        contenido=contenido
                    )
                    db.add(nuevo_mensaje)
                    await db.commit()
                    await db.refresh(nuevo_mensaje)

                    response = {
                        "id": nuevo_mensaje.id,
                        "remitente": miembro.nombre_completo,
                        "contenido": nuevo_mensaje.contenido,
                        "fecha": nuevo_mensaje.fecha_envio.isoformat()
                    }
                    await manager.broadcast(response, hogar_id)

                except json.JSONDecodeError:
                    continue

        except Exception:
            manager.disconnect(websocket, hogar_id)
        break