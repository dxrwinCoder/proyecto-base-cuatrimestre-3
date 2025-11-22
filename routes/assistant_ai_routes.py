from typing import List, Optional
from datetime import datetime, timedelta, date
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from db.database import get_db
from models.miembro import Miembro
from models.tarea import Tarea
from models.evento import Evento
from models.mensaje import Mensaje
from services.tarea_service import (
    listar_tareas_por_miembro,
    listar_tareas_proximas_a_vencer,
)
from services.evento_service import (
    listar_eventos_asignados_en_semana_actual,
    listar_eventos_por_hogar,
    listar_eventos_en_mes_actual,
    listar_eventos_asignados_a_miembro,
)
from services.notificacion_service import listar_notificaciones_por_miembro
from services.mensaje_service import contar_mensajes_no_leidos
from services.assistant_llm import build_messages, get_client, OPENAI_MODEL
from services.assistant_tools import (
    FUNCIONES_DISPONIBLES,
    obtener_prompt_sistema,
)
from utils.logger import setup_logger

router = APIRouter(prefix="/assistant/llm", tags=["assistant-llm"])
logger = setup_logger("assistant_llm_routes")


class HistMessage(BaseModel):
    role: str
    content: str


class LlmRequest(BaseModel):
    mensaje: str
    miembro_id: int
    rol_id: int
    historial: Optional[List[HistMessage]] = None
    respuesta_previa: Optional[str] = None


class LlmReply(BaseModel):
    bubbles: list[dict] = []
    bullets: list[str] = []
    actions: list[dict] = []
    raw_content: str


def _miembro_to_prompt(miembro: Miembro) -> dict:
    """
    Serializa datos basicos del miembro para el prompt dinamico.
    """
    rol_nombre = getattr(getattr(miembro, "rol", None), "nombre", "Miembro")
    return {
        "id": miembro.id,
        "id_hogar": miembro.id_hogar,
        "nombre": getattr(miembro, "nombre_completo", "Usuario"),
        "rol": {"id": miembro.id_rol, "nombre": rol_nombre},
    }


def _build_contexto_rag(
    tareas, proximas, eventos, notifs_len: int, mensajes_no_leidos: int
) -> str:
    """
    Construye un texto corto con datos reales para pasarlo como contexto_rag al LLM.
    Mantenerlo breve para no sobrecargar el prompt.
    """
    partes = []
    if tareas:
        take = tareas[:3]
        resumen_tareas = "; ".join(
            f"[{t.id}] {t.titulo} ({t.estado_actual})" for t in take
        )
        partes.append(f"Tareas del miembro: {resumen_tareas}")
    if proximas:
        take = proximas[:2]
        resumen_proximas = "; ".join(
            f"[{t.id}] {t.titulo} vence {getattr(t, 'fecha_limite', 'pronto')}"
            for t in take
        )
        partes.append(f"Tareas proximas: {resumen_proximas}")
    if eventos:
        take = eventos[:3]
        resumen_eventos = "; ".join(f"[{e.id}] {e.titulo}" for e in take)
        partes.append(f"Eventos activos semana: {resumen_eventos}")
    partes.append(f"Notificaciones sin leer: {notifs_len}")
    partes.append(f"Mensajes no leidos: {mensajes_no_leidos}")
    return "\n".join(partes)


async def _ejecutar_tool_call(tool_call, miembro: Miembro, db: AsyncSession):
    """
    Ejecuta de forma interna las tools declaradas para que el modelo reciba datos reales.
    Se devuelve un dict sencillo serializable a JSON.
    """
    try:
        args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
    except json.JSONDecodeError:
        args = {}

    nombre = tool_call.get("function", {}).get("name")
    miembro_id = args.get("miembro_id") or miembro.id

    if nombre == "consultar_tareas_pendientes_miembro":
        tareas = await listar_tareas_por_miembro(db, miembro_id)
        pendientes = [t for t in tareas if t.estado_actual != "completada"]
        if args.get("ordenar_por_vencimiento"):
            pendientes.sort(key=lambda t: t.fecha_limite or date.max)
        return {
            "total": len(pendientes),
            "items": [
                {
                    "id": t.id,
                    "titulo": t.titulo,
                    "vencimiento": t.fecha_limite.isoformat()
                    if getattr(t, "fecha_limite", None)
                    else None,
                    "estado": t.estado_actual,
                }
                for t in pendientes[:5]
            ],
        }

    if nombre == "consultar_tareas_completadas_miembro":
        dias = args.get("dias_atras", 30)
        corte = datetime.now() - timedelta(days=dias)
        stmt = select(Tarea).where(
            Tarea.asignado_a == miembro_id,
            Tarea.estado == True,  # noqa: E712
            Tarea.estado_actual == "completada",
            Tarea.fecha_actualizacion >= corte,
        )
        res = await db.execute(stmt)
        tareas = res.scalars().all()
        return {
            "total": len(tareas),
            "items": [
                {
                    "id": t.id,
                    "titulo": t.titulo,
                    "completada": getattr(t, "fecha_actualizacion", None),
                }
                for t in tareas[:5]
            ],
        }

    if nombre == "consultar_eventos_relacionados_miembro":
        eventos = await listar_eventos_asignados_a_miembro(db, miembro_id)
        if args.get("solo_activos", True):
            eventos = [e for e in eventos if getattr(e, "estado", True)]
        return {
            "total": len(eventos),
            "items": [{"id": e.id, "titulo": e.titulo} for e in eventos[:5]],
        }

    if nombre == "consultar_comentarios_no_leidos":
        # No hay flag de lectura en comentarios; devolvemos 0 y delegamos a notificaciones si aplica.
        return {"total": 0, "detalle": "No hay campo de lectura en comentarios, usar notificaciones"}

    if nombre == "consultar_mensajes_no_leidos":
        tipo = args.get("tipo", "todos")
        stmt = select(Mensaje).where(Mensaje.estado == 1, Mensaje.leido == False)  # noqa: E712
        if tipo == "directo":
            stmt = stmt.where(Mensaje.id_destinatario == miembro_id)
        elif tipo == "hogar":
            stmt = stmt.where(
                Mensaje.id_destinatario.is_(None),
                Mensaje.id_hogar == miembro.id_hogar,
            )
        else:
            stmt = stmt.where(
                Mensaje.id_hogar == miembro.id_hogar,
                or_(Mensaje.id_destinatario == miembro_id, Mensaje.id_destinatario.is_(None)),
            )
        msgs = (await db.execute(stmt)).scalars().all()
        return {"total": len(msgs), "ids": [m.id for m in msgs[:5]]}

    if nombre == "consultar_eventos":
        tipo = args.get("tipo_consulta")
        if tipo == "todos":
            eventos = await listar_eventos_por_hogar(db, miembro.id_hogar)
        elif tipo == "mes_actual":
            eventos = await listar_eventos_en_mes_actual(db, miembro.id_hogar)
        elif tipo == "semana_actual":
            eventos = await listar_eventos_asignados_en_semana_actual(db, miembro.id)
        elif tipo == "asignados_miembro":
            mid = args.get("miembro_id") or miembro.id
            eventos = await listar_eventos_asignados_a_miembro(db, mid)
        else:
            eventos = []
        return {
            "total": len(eventos),
            "items": [{"id": e.id, "titulo": e.titulo} for e in eventos[:5]],
        }

    if nombre == "consultar_tareas":
        stmt = select(Tarea).where(Tarea.id_hogar == miembro.id_hogar, Tarea.estado == True)  # noqa: E712
        estado = args.get("estado")
        if estado and estado != "todos":
            stmt = stmt.where(Tarea.estado_actual == estado)
        asignado = args.get("asignado_a")
        if asignado:
            stmt = stmt.where(Tarea.asignado_a == asignado)
        buscar = args.get("buscar_texto")
        if buscar:
            like = f"%{buscar}%"
            stmt = stmt.where(or_(Tarea.titulo.ilike(like), Tarea.descripcion.ilike(like)))
        tareas = (await db.execute(stmt)).scalars().all()
        return {
            "total": len(tareas),
            "items": [
                {
                    "id": t.id,
                    "titulo": t.titulo,
                    "estado": t.estado_actual,
                    "asignado_a": t.asignado_a,
                }
                for t in tareas[:5]
            ],
        }

    if nombre == "crear_tarea":
        # Falta informacion critica (id_hogar y creado_por); se devuelve un mensaje instructivo.
        return {
            "error": "No se puede crear tarea sin id_hogar y creado_por. Usa el flujo de creacion del backend.",
            "requerido": ["titulo", "asignado_a", "id_hogar", "creado_por"],
        }

    if nombre == "obtener_resumen_diario":
        # Reutilizamos otras tools basicas para armar el resumen.
        tareas = await _ejecutar_tool_call(
            {"function": {"name": "consultar_tareas_pendientes_miembro", "arguments": json.dumps({"miembro_id": miembro_id})}},
            miembro,
            db,
        )
        eventos = await _ejecutar_tool_call(
            {"function": {"name": "consultar_eventos", "arguments": json.dumps({"tipo_consulta": "semana_actual"})}},
            miembro,
            db,
        )
        mensajes = await _ejecutar_tool_call(
            {"function": {"name": "consultar_mensajes_no_leidos", "arguments": json.dumps({"miembro_id": miembro_id, "tipo": "todos"})}},
            miembro,
            db,
        )
        return {
            "tareas_pendientes": tareas,
            "eventos_semana": eventos,
            "mensajes_no_leidos": mensajes,
        }

    return {"detalle": f"Tool {nombre} no implementada"}


@router.post("", response_model=LlmReply)
async def responder_con_llm(req: LlmRequest, db: AsyncSession = Depends(get_db)):
    """
    Orquesta una llamada al LLM usando datos reales (tareas/eventos/notifs/mensajes) como contexto RAG.
    - Mantiene historial corto y respuesta previa para coherencia.
    - Devuelve JSON listo para UI: bubbles/bullets/actions (si el modelo lo respeta).
    """
    miembro = await db.get(Miembro, req.miembro_id)
    if not miembro or not miembro.estado:
        logger.warning("Miembro no encontrado o inactivo: %s", req.miembro_id)
        raise HTTPException(status_code=404, detail="Miembro no encontrado")

    tareas = await listar_tareas_por_miembro(db, req.miembro_id)
    proximas = await listar_tareas_proximas_a_vencer(
        db, miembro.id_hogar, datetime.now() + timedelta(days=3)
    )
    eventos = await listar_eventos_asignados_en_semana_actual(db, req.miembro_id)
    notifs = await listar_notificaciones_por_miembro(db, req.miembro_id)
    mensajes_no_leidos = await contar_mensajes_no_leidos(db, req.miembro_id)

    contexto_rag = _build_contexto_rag(
        tareas=tareas or [],
        proximas=proximas or [],
        eventos=eventos or [],
        notifs_len=len(notifs),
        mensajes_no_leidos=mensajes_no_leidos,
    )

    historial_llm = (
        [{"role": h.role, "content": h.content} for h in req.historial]
        if req.historial
        else None
    )

    # Construir mensajes base con prompt dinamico y contexto RAG.
    system_prompt = obtener_prompt_sistema(_miembro_to_prompt(miembro))
    messages = build_messages(
        mensaje_usuario=req.mensaje,
        historial_corto=historial_llm,
        respuesta_previa=req.respuesta_previa,
        contexto_rag=contexto_rag,
        system_prompt=system_prompt,
    )

    client = get_client()
    completion = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        tools=FUNCIONES_DISPONIBLES,
        tool_choice="auto",
    )

    choice = completion.choices[0].message
    tool_calls = getattr(choice, "tool_calls", None)

    # Si el modelo pidio tools, las ejecutamos y hacemos una segunda llamada.
    if tool_calls:
        assistant_msg = {
            "role": "assistant",
            "content": choice.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        }
        tool_messages = []
        for tc in tool_calls:
            resultado = await _ejecutar_tool_call(
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                },
                miembro,
                db,
            )
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": json.dumps(resultado, default=str),
                }
            )

        messages_with_tools = messages + [assistant_msg] + tool_messages
        completion = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages_with_tools,
            tools=FUNCIONES_DISPONIBLES,
            tool_choice="none",
        )
        choice = completion.choices[0].message

    # Extraer el mensaje principal del LLM
    content = choice.content or ""

    bubbles = []
    bullets = []
    actions = []
    try:
        parsed = json.loads(content)
        bubbles = parsed.get("bubbles", [])
        bullets = parsed.get("bullets", [])
        actions = parsed.get("actions", [])
    except json.JSONDecodeError:
        logger.warning("Respuesta del LLM no es JSON parseable. Se devuelve raw_content.")

    return LlmReply(
        bubbles=bubbles,
        bullets=bullets,
        actions=actions,
        raw_content=content,
    )
