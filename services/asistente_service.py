"""
Servicio de orquestacion del asistente IA.
- Ejecuta tools declaradas (FUNCIONES_DISPONIBLES) sobre tus servicios reales.
- Llama al modelo LLM con function-calling y devuelve una respuesta estructurada.
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List
import json

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from services.assistant_llm import get_client, build_messages, OPENAI_MODEL
from services.assistant_tools import FUNCIONES_DISPONIBLES, obtener_prompt_sistema
from services.evento_service import (
    listar_eventos_activos,
    listar_eventos_en_mes_actual,
    listar_eventos_asignados_en_mes_actual,
    listar_eventos_asignados_en_semana_actual,
    listar_eventos_asignados_a_miembro,
)
from services.tarea_service import (
    listar_tareas_por_miembro,
    listar_todas_tareas_hogar,
    crear_tarea as crear_tarea_service,
)
from services.mensaje_service import listar_conversacion_directa
from services.notificacion_service import listar_notificaciones_por_miembro
from schemas.asistente import ConsultaIA, RespuestaIA, BotonAccion, Sugerencia
from schemas.tarea import TareaCreate
from models.comentario_tarea import ComentarioTarea
from models.miembro import Miembro
from utils.logger import setup_logger

logger = setup_logger("asistente_service")


async def ejecutar_funcion(
    nombre_funcion: str,
    argumentos: Dict[str, Any],
    db: AsyncSession,
    miembro_actual: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Ejecuta una funcion solicitada por el LLM (function-call) usando los servicios reales.
    Devuelve un dict serializable con los datos o un mensaje de error.
    """
    try:
        hogar_id = miembro_actual.get("id_hogar")
        miembro_id = miembro_actual.get("id")

        if nombre_funcion == "consultar_tareas_pendientes_miembro":
            miembro_consulta = argumentos.get("miembro_id", miembro_id)
            ordenar_vencimiento = argumentos.get("ordenar_por_vencimiento", True)

            tareas = await listar_tareas_por_miembro(db, miembro_consulta)
            tareas_pendientes = [
                t
                for t in tareas
                if t.estado_actual in ["pendiente", "en_progreso"] and t.estado
            ]

            if ordenar_vencimiento:
                tareas_pendientes.sort(
                    key=lambda x: x.fecha_limite if x.fecha_limite else date.max
                )

            hoy = date.today()
            tarea_proxima_vencer = next(
                (t for t in tareas_pendientes if t.fecha_limite and t.fecha_limite >= hoy),
                None,
            )

            return {
                "success": True,
                "data": [
                    {
                        "id": t.id,
                        "titulo": t.titulo,
                        "descripcion": t.descripcion,
                        "estado": t.estado_actual,
                        "fecha_limite": t.fecha_limite.isoformat()
                        if t.fecha_limite
                        else None,
                        "categoria": t.categoria,
                        "dias_restantes": (t.fecha_limite - hoy).days
                        if t.fecha_limite
                        else None,
                    }
                    for t in tareas_pendientes
                ],
                "total": len(tareas_pendientes),
                "tarea_proxima_vencer": {
                    "id": tarea_proxima_vencer.id,
                    "titulo": tarea_proxima_vencer.titulo,
                    "dias_restantes": (tarea_proxima_vencer.fecha_limite - hoy).days,
                }
                if tarea_proxima_vencer
                else None,
            }

        if nombre_funcion == "consultar_tareas_completadas_miembro":
            miembro_consulta = argumentos.get("miembro_id", miembro_id)
            dias_atras = argumentos.get("dias_atras", 30)
            fecha_limite = date.today() - timedelta(days=dias_atras)

            tareas = await listar_tareas_por_miembro(db, miembro_consulta)
            tareas_completadas = [
                t
                for t in tareas
                if t.estado_actual == "completada"
                and t.estado
                and (not t.fecha_actualizacion or t.fecha_actualizacion.date() >= fecha_limite)
            ]

            return {
                "success": True,
                "data": [
                    {
                        "id": t.id,
                        "titulo": t.titulo,
                        "fecha_completada": t.fecha_actualizacion.isoformat()
                        if t.fecha_actualizacion
                        else None,
                        "categoria": t.categoria,
                    }
                    for t in tareas_completadas
                ],
                "total": len(tareas_completadas),
                "periodo_dias": dias_atras,
            }

        if nombre_funcion == "consultar_eventos_relacionados_miembro":
            miembro_consulta = argumentos.get("miembro_id", miembro_id)
            solo_activos = argumentos.get("solo_activos", True)

            eventos = await listar_eventos_asignados_a_miembro(db, miembro_consulta)
            if solo_activos:
                eventos = [e for e in eventos if e.estado]

            return {
                "success": True,
                "data": [
                    {
                        "id": e.id,
                        "titulo": e.titulo,
                        "descripcion": e.descripcion,
                        "fecha_hora": e.fecha_hora.isoformat() if e.fecha_hora else None,
                        "ubicacion": e.ubicacion,
                    }
                    for e in eventos
                ],
                "total": len(eventos),
            }

        if nombre_funcion == "consultar_comentarios_no_leidos":
            miembro_consulta = argumentos.get("miembro_id", miembro_id)
            tareas = await listar_tareas_por_miembro(db, miembro_consulta)
            tareas_ids = [t.id for t in tareas]
            if not tareas_ids:
                return {"success": True, "data": [], "total": 0}

            stmt = (
                select(ComentarioTarea)
                .where(
                    ComentarioTarea.id_tarea.in_(tareas_ids),
                    ComentarioTarea.id_miembro != miembro_consulta,
                )
                .order_by(ComentarioTarea.fecha_creacion.desc())
            )
            comentarios = (await db.execute(stmt)).scalars().all()

            return {
                "success": True,
                "data": [
                    {
                        "id": c.id,
                        "contenido": c.contenido,
                        "tarea_id": c.id_tarea,
                        "tarea_titulo": next(
                            (t.titulo for t in tareas if t.id == c.id_tarea), "Tarea"
                        ),
                        "fecha": c.fecha_creacion.isoformat() if c.fecha_creacion else None,
                    }
                    for c in comentarios
                ],
                "total": len(comentarios),
            }

        if nombre_funcion == "consultar_mensajes_no_leidos":
            miembro_consulta = argumentos.get("miembro_id", miembro_id)
            tipo = argumentos.get("tipo", "todos")

            notificaciones = await listar_notificaciones_por_miembro(db, miembro_consulta)
            mensajes_notif = [n for n in notificaciones if "mensaje" in n.tipo.lower()]

            mensajes_directos = []
            if tipo in ["directo", "todos"]:
                stmt_miembros = select(Miembro).where(
                    Miembro.id_hogar == hogar_id,
                    Miembro.id != miembro_consulta,
                    Miembro.estado == True,  # noqa: E712
                )
                otros_miembros = (await db.execute(stmt_miembros)).scalars().all()

                fecha_limite = datetime.now() - timedelta(days=7)
                for otro in otros_miembros:
                    conversacion = await listar_conversacion_directa(
                        db, hogar_id, miembro_consulta, otro.id
                    )
                    mensajes_recientes = [
                        m
                        for m in conversacion
                        if m.fecha_envio
                        and m.fecha_envio >= fecha_limite
                        and m.id_remitente != miembro_consulta
                    ]
                    mensajes_directos.extend(mensajes_recientes)

            return {
                "success": True,
                "data": {
                    "notificaciones": len(mensajes_notif),
                    "mensajes_directos": [
                        {
                            "id": m.id,
                            "contenido": m.contenido[:100],
                            "remitente_id": m.id_remitente,
                            "fecha": m.fecha_envio.isoformat() if m.fecha_envio else None,
                        }
                        for m in mensajes_directos[:10]
                    ],
                    "total_mensajes_directos": len(mensajes_directos),
                },
                "total": len(mensajes_notif) + len(mensajes_directos),
            }

        if nombre_funcion == "obtener_resumen_diario":
            miembro_consulta = argumentos.get("miembro_id", miembro_id)
            tareas_pend = await ejecutar_funcion(
                "consultar_tareas_pendientes_miembro",
                {"miembro_id": miembro_consulta, "ordenar_por_vencimiento": True},
                db,
                miembro_actual,
            )
            eventos_rel = await ejecutar_funcion(
                "consultar_eventos_relacionados_miembro",
                {"miembro_id": miembro_consulta, "solo_activos": True},
                db,
                miembro_actual,
            )
            comentarios = await ejecutar_funcion(
                "consultar_comentarios_no_leidos",
                {"miembro_id": miembro_consulta},
                db,
                miembro_actual,
            )
            mensajes = await ejecutar_funcion(
                "consultar_mensajes_no_leidos",
                {"miembro_id": miembro_consulta, "tipo": "todos"},
                db,
                miembro_actual,
            )
            return {
                "success": True,
                "data": {
                    "tareas_pendientes": tareas_pend,
                    "eventos_relacionados": eventos_rel,
                    "comentarios_no_leidos": comentarios,
                    "mensajes_no_leidos": mensajes,
                },
            }

        if nombre_funcion == "consultar_eventos":
            tipo = argumentos.get("tipo_consulta", "todos")
            if tipo == "todos":
                eventos = await listar_eventos_activos(db, hogar_id)
            elif tipo == "mes_actual":
                eventos = await listar_eventos_en_mes_actual(db, hogar_id)
            elif tipo == "semana_actual":
                eventos = await listar_eventos_asignados_en_semana_actual(db, miembro_id)
            elif tipo == "asignados_miembro":
                miembro_id_consulta = argumentos.get("miembro_id", miembro_id)
                eventos = await listar_eventos_asignados_en_mes_actual(db, miembro_id_consulta)
            else:
                eventos = []

            return {
                "success": True,
                "data": [
                    {
                        "id": e.id,
                        "titulo": e.titulo,
                        "descripcion": e.descripcion,
                        "fecha_hora": e.fecha_hora.isoformat() if e.fecha_hora else None,
                        "ubicacion": e.ubicacion,
                    }
                    for e in eventos
                ],
                "total": len(eventos),
            }

        if nombre_funcion == "consultar_tareas":
            estado = argumentos.get("estado", "todos")
            asignado_a = argumentos.get("asignado_a")
            buscar_texto = argumentos.get("buscar_texto")

            tareas = await listar_todas_tareas_hogar(db, hogar_id)
            if estado != "todos":
                tareas = [t for t in tareas if t.estado_actual == estado]
            if asignado_a:
                tareas = [t for t in tareas if t.asignado_a == asignado_a]
            if buscar_texto:
                like = buscar_texto.lower()
                tareas = [
                    t
                    for t in tareas
                    if like in t.titulo.lower()
                    or (t.descripcion and like in t.descripcion.lower())
                ]

            return {
                "success": True,
                "data": [
                    {
                        "id": t.id,
                        "titulo": t.titulo,
                        "descripcion": t.descripcion,
                        "estado": t.estado_actual,
                        "asignado_a": t.asignado_a,
                        "fecha_vencimiento": t.fecha_limite.isoformat()
                        if t.fecha_limite
                        else None,
                    }
                    for t in tareas
                ],
                "total": len(tareas),
            }

        if nombre_funcion == "crear_tarea":
            titulo = argumentos.get("titulo")
            if not titulo:
                return {"success": False, "error": "El titulo es requerido"}

            tarea_data = TareaCreate(
                titulo=titulo,
                descripcion=argumentos.get("descripcion", ""),
                asignado_a=argumentos.get("asignado_a", miembro_id),
                fecha_limite=argumentos.get("fecha_vencimiento"),
                categoria=argumentos.get("categoria", "limpieza"),
                id_hogar=hogar_id,
            )

            tarea = await crear_tarea_service(db, tarea_data, miembro_id)
            await db.flush()

            return {
                "success": True,
                "data": {
                    "id": tarea.id,
                    "titulo": tarea.titulo,
                    "mensaje": f"Tarea '{titulo}' creada exitosamente",
                },
            }

        return {"success": False, "error": f"Funcion '{nombre_funcion}' no implementada"}

    except Exception as e:
        logger.error(f"Error al ejecutar funcion {nombre_funcion}: {str(e)}")
        return {"success": False, "error": str(e)}


def generar_sugerencias_y_botones(
    intencion: str,
    datos_obtenidos: Dict[str, Any],
    miembro_actual: Dict[str, Any],
) -> tuple[List[Sugerencia], List[BotonAccion]]:
    """
    Construye sugerencias y botones accionables para el frontend segun la intencion detectada.
    """
    sugerencias: List[Sugerencia] = []
    botones: List[BotonAccion] = []

    if intencion == "consultar_tareas_pendientes_miembro":
        total = datos_obtenidos.get("total", 0)
        tarea_proxima = datos_obtenidos.get("tarea_proxima_vencer")
        if total > 0 and tarea_proxima:
            dias = tarea_proxima.get("dias_restantes", 0)
            if dias <= 3:
                sugerencias.append(
                    Sugerencia(
                        texto=f"ALERTA: Tienes una tarea cerca de vencer: '{tarea_proxima['titulo']}' en {dias} dias. Date prisa!",
                        tipo="alerta",
                    )
                )
                sugerencias.append(
                    Sugerencia(
                        texto="Tip: Quieres que te ayude a organizar cada accion para optimizar tu tiempo?",
                        tipo="consejo",
                    )
                )
        botones.append(
            BotonAccion(
                texto="Ver mis tareas pendientes",
                accion="ver_tareas",
                parametros={"estado": "pendiente"},
            )
        )
        botones.append(BotonAccion(texto="Crear nueva tarea", accion="crear_tarea"))

    elif intencion == "consultar_eventos_relacionados_miembro":
        total = datos_obtenidos.get("total", 0)
        if total > 0:
            sugerencias.append(
                Sugerencia(texto=f"Calendario: Tienes {total} evento(s) donde estas relacionado. No olvides revisarlos.", tipo="sugerencia")
            )
            botones.append(BotonAccion(texto="Ver mi calendario", accion="ver_calendario"))

    elif intencion == "consultar_comentarios_no_leidos":
        total = datos_obtenidos.get("total", 0)
        if total > 0:
            sugerencias.append(
                Sugerencia(texto=f"Comentarios: Tienes {total} comentario(s) nuevos en tus tareas. Revisa las conversaciones.", tipo="alerta")
            )
            botones.append(BotonAccion(texto="Ver comentarios", accion="ver_comentarios"))

    elif intencion == "consultar_mensajes_no_leidos":
        total = datos_obtenidos.get("total", 0)
        if total > 0:
            sugerencias.append(
                Sugerencia(texto=f"Mensajes: Tienes {total} mensaje(s) sin leer. Revisa tus conversaciones.", tipo="alerta")
            )
            botones.append(BotonAccion(texto="Ver mensajes", accion="ver_mensajes"))

    elif intencion == "crear_tarea":
        sugerencias.append(
            Sugerencia(
                texto="Tarea creada exitosamente. Quieres crear otra?",
                tipo="sugerencia",
            )
        )
        botones.append(
            BotonAccion(
                texto="Crear tarea de limpieza",
                accion="crear_tarea_limpieza",
                parametros={"categoria": "limpieza"},
            )
        )
        botones.append(BotonAccion(texto="Ver mis tareas", accion="ver_tareas"))

    return sugerencias, botones


async def procesar_consulta_ia(
    consulta: ConsultaIA,
    db: AsyncSession,
    miembro_actual: Dict[str, Any],
) -> RespuestaIA:
    """
    Orquesta la conversacion con el LLM:
    - Construye prompt de sistema dinamico.
    - Llama al modelo con tools para obtener intencion.
    - Ejecuta las tools solicitadas y hace una segunda llamada con resultados.
    - Genera sugerencias/botones listos para el frontend.
    """
    try:
        prompt_sistema = obtener_prompt_sistema(miembro_actual)
        historial = consulta.historial_conversacion or []

        # Llamada inicial con tools habilitadas
        messages = build_messages(
            mensaje_usuario=consulta.mensaje,
            historial_corto=historial,
            system_prompt=prompt_sistema,
        )
        client = get_client()
        completion = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=FUNCIONES_DISPONIBLES,
            tool_choice="auto",
        )

        choice = completion.choices[0].message
        acciones_realizadas: List[str] = []
        datos_obtenidos: Dict[str, Any] = {}
        intencion_detectada: Optional[str] = None

        # Si el modelo solicita tools, se ejecutan y se rehace la llamada para la respuesta final.
        tool_calls = getattr(choice, "tool_calls", None)
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
                resultado = await ejecutar_funcion(
                    tc.function.name,
                    json.loads(tc.function.arguments or "{}"),
                    db,
                    miembro_actual,
                )
                acciones_realizadas.append(tc.function.name)
                datos_obtenidos[tc.function.name] = resultado
                intencion_detectada = tc.function.name
                tool_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": json.dumps(resultado, ensure_ascii=False, default=str),
                    }
                )

            follow_messages = messages + [assistant_msg] + tool_messages
            completion = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=follow_messages,
                tools=FUNCIONES_DISPONIBLES,
                tool_choice="none",
            )
            choice = completion.choices[0].message

        respuesta_final = choice.content or "No pude generar una respuesta en este momento."

        # Intentar deducir intencion si no hubo tool_call
        if not intencion_detectada:
            msg_lower = consulta.mensaje.lower()
            if "tarea" in msg_lower and "pendiente" in msg_lower:
                intencion_detectada = "consultar_tareas_pendientes_miembro"
            elif "evento" in msg_lower:
                intencion_detectada = "consultar_eventos_relacionados_miembro"
            elif "comentario" in msg_lower or "mensaje" in msg_lower:
                intencion_detectada = "consultar_mensajes_no_leidos"

        sugerencias, botones = generar_sugerencias_y_botones(
            intencion_detectada or "",
            datos_obtenidos.get(intencion_detectada or "", {}),
            miembro_actual,
        )

        return RespuestaIA(
            respuesta=respuesta_final,
            intencion_detectada=intencion_detectada,
            acciones_realizadas=acciones_realizadas or None,
            datos_obtenidos=datos_obtenidos or None,
            sugerencias=sugerencias or None,
            botones_accion=botones or None,
            timestamp=datetime.now(),
            tipo_respuesta="lista" if sugerencias else "texto",
        )

    except Exception as e:
        logger.error(f"Error al procesar consulta IA: {str(e)}")
        return RespuestaIA(
            respuesta=f"Lo siento, ocurrio un error al procesar tu consulta: {str(e)}",
            timestamp=datetime.now(),
        )
