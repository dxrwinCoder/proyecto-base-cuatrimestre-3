from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.miembro import Miembro
from services.tarea_service import (
    listar_tareas_por_miembro,
    listar_tareas_proximas_a_vencer,
)
from services.evento_service import listar_eventos_asignados_en_semana_actual
from services.notificacion_service import listar_notificaciones_por_miembro
from services.mensaje_service import contar_mensajes_no_leidos
from utils.logger import setup_logger

router = APIRouter(prefix="/assistant", tags=["assistant"])
logger = setup_logger("assistant_routes")


class AssistantQuery(BaseModel):
    mensaje: str
    miembro_id: int
    rol_id: int


class AssistantBubble(BaseModel):
    origen: str
    texto: str


class AssistantAction(BaseModel):
    label: str
    action: str
    payload: dict = Field(default_factory=dict)


class AssistantReply(BaseModel):
    bubbles: list[AssistantBubble]
    bullets: list[str] = []
    actions: list[AssistantAction] = []


@router.post("/query", response_model=AssistantReply)
async def responder(query: AssistantQuery, db: AsyncSession = Depends(get_db)):
    """
    Construye la respuesta conversacional del asistente en base a los datos del usuario.
    Consulta tareas, eventos, notificaciones y mensajes para dar contexto inmediato.
    """
    miembro = await db.get(Miembro, query.miembro_id)
    if not miembro or not miembro.estado:
        logger.warning("Miembro no encontrado o inactivo: %s", query.miembro_id)
        raise HTTPException(status_code=404, detail="Miembro no encontrado")

    # Rol 2: asistente operativo con foco en tareas/eventos/notificaciones.
    # Se pueden añadir más ramas por rol si el producto lo requiere.
    tareas = await listar_tareas_por_miembro(db, query.miembro_id)
    pendientes = [t for t in tareas if t.estado_actual != "completada"]
    proximas = await listar_tareas_proximas_a_vencer(
        db, miembro.id_hogar, datetime.now() + timedelta(days=3)
    )
    eventos = await listar_eventos_asignados_en_semana_actual(db, query.miembro_id)
    notifs = await listar_notificaciones_por_miembro(db, query.miembro_id)
    mensajes_no_leidos = await contar_mensajes_no_leidos(db, query.miembro_id)

    # Texto principal con tono de asistente.
    urgente = ""
    if proximas:
        tarea_urgente = proximas[0]
        fecha_str = (
            tarea_urgente.fecha_limite.isoformat()
            if getattr(tarea_urgente, "fecha_limite", None)
            else "pronto"
        )
        urgente = f" La más cercana a vencer es '{tarea_urgente.titulo}' para {fecha_str}."

    texto_tareas = (
        f"Hey! Tienes {len(pendientes)} tareas pendientes.{urgente} "
        "¿Quieres que te ayude a organizar acciones rápidas?"
    )

    bullets: list[str] = []
    if proximas:
        bullets.append(f"Prioriza: {proximas[0].titulo}")
    if eventos:
        bullets.append(f"Eventos activos esta semana: {len(eventos)}")
    if notifs:
        bullets.append(f"Tienes {len(notifs)} notificaciones sin leer")
    if mensajes_no_leidos:
        bullets.append(f"Tienes {mensajes_no_leidos} mensajes nuevos en el chat")

    actions: list[AssistantAction] = [
        AssistantAction(label="Ver tareas", action="open_tasks", payload={}),
        AssistantAction(label="Ver calendario", action="open_calendar", payload={}),
        AssistantAction(label="Ir al chat", action="open_chat", payload={}),
    ]

    if proximas:
        actions.append(
            AssistantAction(
                label="Marcar como completada",
                action="complete_task",
                payload={"tarea_id": proximas[0].id},
            )
        )

    respuesta = AssistantReply(
        bubbles=[
            AssistantBubble(origen="assistant", texto=texto_tareas),
            AssistantBubble(
                origen="assistant",
                texto="Puedo crear una lista de pasos, reprogramar o asignar tareas. ¿Qué hacemos?",
            ),
        ],
        bullets=bullets,
        actions=actions,
    )

    logger.info("Respuesta de asistente generada para miembro %s", query.miembro_id)
    return respuesta
