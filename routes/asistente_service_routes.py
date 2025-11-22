from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import get_db
from models.miembro import Miembro
from services.asistente_service import procesar_consulta_ia
from schemas.asistente import ConsultaIA
from utils.logger import setup_logger

router = APIRouter(prefix="/assistant/agent", tags=["assistant-agent"])
logger = setup_logger("asistente_service_routes")


class HistorialItem(BaseModel):
    """Elemento de historial de la conversacion."""

    role: str
    content: str


class ConsultaRequest(BaseModel):
    """Entrada del frontend para el agente."""

    mensaje: str
    miembro_id: int
    rol_id: int
    historial: Optional[List[HistorialItem]] = None


class Burbuja(BaseModel):
    """Burbuja de chat para el frontend."""

    from_: str = Field(..., alias="from")
    text: str

    class Config:
        allow_population_by_field_name = True
        fields = {"from_": "from"}


class ActionChip(BaseModel):
    """Chip de accion para el frontend."""

    label: str
    action: str
    payload: dict = Field(default_factory=dict)


class AgentReply(BaseModel):
    """Respuesta estructurada para pintarse como la maqueta."""

    bubbles: List[Burbuja]
    bullets: List[str] = []
    actions: List[ActionChip] = []
    raw: str
    intencion: Optional[str] = None


def _miembro_a_dict(miembro: Miembro) -> dict:
    """Serializa datos minimos del miembro para el prompt."""
    rol_nombre = getattr(getattr(miembro, "rol", None), "nombre", "Miembro")
    return {
        "id": miembro.id,
        "id_hogar": miembro.id_hogar,
        "nombre": getattr(miembro, "nombre_completo", "Usuario"),
        "rol": {"id": miembro.id_rol, "nombre": rol_nombre},
    }


@router.post("", response_model=AgentReply)
async def responder_agente(
    body: ConsultaRequest, db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para el agente IA basado en services.asistente_service.
    Devuelve la estructura bubbles/bullets/actions lista para el frontend.
    """
    # Cargar miembro junto con su rol para evitar lazy-load (MissingGreenlet)
    stmt = (
        select(Miembro)
        .options(selectinload(Miembro.rol))
        .where(Miembro.id == body.miembro_id)
    )
    miembro = (await db.execute(stmt)).scalar_one_or_none()
    if not miembro or not miembro.estado:
        logger.warning("Miembro no encontrado o inactivo: %s", body.miembro_id)
        raise HTTPException(status_code=404, detail="Miembro no encontrado")

    miembro_actual = _miembro_a_dict(miembro)
    consulta = ConsultaIA(
        mensaje=body.mensaje,
        historial_conversacion=[
            {"role": h.role, "content": h.content} for h in (body.historial or [])
        ],
    )

    respuesta = await procesar_consulta_ia(consulta, db, miembro_actual)

    # Construir respuesta para UI tipo maqueta
    bubbles = [Burbuja(from_="assistant", text=respuesta.respuesta)]
    bullets = [s.texto for s in respuesta.sugerencias] if respuesta.sugerencias else []
    actions = (
        [
            ActionChip(label=b.texto, action=b.accion, payload=b.parametros or {})
            for b in (respuesta.botones_accion or [])
        ]
    )

    return AgentReply(
        bubbles=bubbles,
        bullets=bullets,
        actions=actions,
        raw=respuesta.respuesta,
        intencion=respuesta.intencion_detectada,
    )
