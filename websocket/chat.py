from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from models.miembro import Miembro
from websocket.chat_manager import manager
from websocket.security import decode_jwt
from db.database import get_db
from services.mensaje_service import enviar_mensaje_directo
import json


async def get_miembro_from_token(token: str, db: AsyncSession):
    payload = decode_jwt(token)
    if not payload or "sub" not in payload:
        return None
    miembro_id = int(payload["sub"])
    miembro = await db.get(Miembro, miembro_id)
    return miembro if miembro and miembro.estado else None


async def chat_websocket(websocket: WebSocket, token: str, destinatario_id: int):
    """
    WebSocket para chat 1 a 1 entre miembros del mismo hogar.
    - Autentica por token JWT.
    - Valida que destinatario pertenezca al mismo hogar.
    - Persiste mensaje y lo envía a ambos participantes conectados a la conversación.
    """
    async for db in get_db():
        miembro = await get_miembro_from_token(token, db)
        if not miembro:
            await websocket.close(code=4001, reason="Token inválido")
            return

        destinatario = await db.get(Miembro, destinatario_id)
        if not destinatario or destinatario.id_hogar != miembro.id_hogar:
            await websocket.close(code=4003, reason="Destinatario inválido")
            return

        conv_key = await manager.connect(websocket, miembro.id, destinatario_id)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    body = json.loads(data)
                    contenido = body.get("contenido", "").strip()
                    if not contenido:
                        continue

                    mensaje = await enviar_mensaje_directo(
                        db,
                        id_hogar=miembro.id_hogar,
                        remitente_id=miembro.id,
                        destinatario_id=destinatario_id,
                        contenido=contenido,
                    )
                    await db.commit()
                    response = {
                        "id": mensaje.id,
                        "remitente_id": miembro.id,
                        "destinatario_id": destinatario_id,
                        "contenido": mensaje.contenido,
                        "fecha": mensaje.fecha_envio.isoformat(),
                    }
                    await manager.send_to_conversation(response, conv_key)

                except json.JSONDecodeError:
                    continue
        except Exception:
            manager.disconnect(websocket, conv_key)
        break
