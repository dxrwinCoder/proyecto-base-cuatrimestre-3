from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.evento import EventoCreate, Evento
from services.evento_service import (
    crear_evento,
    listar_eventos_asignados_a_miembro,
    listar_eventos_asignados_en_mes_actual as service_listar_eventos_asignados_en_mes_actual,
    listar_eventos_asignados_en_semana_actual as service_listar_eventos_asignados_en_semana_actual,
    listar_eventos_por_hogar as service_listar_eventos_por_hogar,
    listar_eventos_activos,
    listar_eventos_en_mes_actual,
    listar_tareas_de_evento,
    listar_tareas_de_evento_por_estado,
    miembros_relacionados_a_evento,
    quitar_tarea_de_evento,
    obtener_evento,
)
from services.tarea_service import (
    asignar_tarea_a_evento,
    reasignar_miembro_tarea_evento,
)
from utils.auth import obtener_miembro_actual
from utils.permissions import require_permission
from models.miembro import Miembro

router = APIRouter(prefix="/eventos", tags=["Eventos"])


@router.post("/", response_model=Evento, status_code=status.HTTP_201_CREATED)
async def crear_evento_endpoint(
    evento: EventoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "crear")),
):
    try:
        resultado = await crear_evento(db, evento.dict())
        await db.commit()
        return resultado
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear evento: {str(e)}",
        )


@router.get("/hogar/actuales", response_model=list[Evento])
async def eventos_mes_actual(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "leer")),
):
    """
    Eventos activos del hogar del usuario cuyo datetime cae en el mes actual del sistema.
    """
    return await listar_eventos_en_mes_actual(db, current_user.id_hogar)


@router.get("/hogar/activos", response_model=list[Evento])
async def eventos_activos(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "leer")),
):
    """
    Eventos activos (estado=True) del hogar del usuario.
    """
    return await listar_eventos_activos(db, current_user.id_hogar)


@router.get("/mis-eventos", response_model=list[Evento])
async def eventos_asignados(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    return await listar_eventos_asignados_a_miembro(db, current_user.id)


@router.get("/mis-eventos/mes-actual", response_model=list[Evento])
async def eventos_asignados_mes_actual(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    return await service_listar_eventos_asignados_en_mes_actual(db, current_user.id)


@router.get("/mis-eventos/semana-actual", response_model=list[Evento])
async def eventos_asignados_semana_actual(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(obtener_miembro_actual),
):
    return await service_listar_eventos_asignados_en_semana_actual(db, current_user.id)


@router.get(
    "/hogar/{hogar_id}",
    response_model=list[Evento],
)
async def listar_eventos_por_hogar_endpoint(
    hogar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "leer")),
):
    # Validar que el usuario consulte su propio hogar, salvo que su rol sea admin.
    if current_user.id_rol != 1 and current_user.id_hogar != hogar_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver eventos de otro hogar",
        )
    return await service_listar_eventos_por_hogar(db, hogar_id)


@router.get("/{evento_id}/tareas", response_model=list)
async def tareas_de_evento(
    evento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "leer")),
):
    evento = await obtener_evento(db, evento_id)
    if not evento or (
        current_user.id_rol != 1 and evento.id_hogar != current_user.id_hogar
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
        )

    return await listar_tareas_de_evento(db, evento_id)


@router.get("/{evento_id}/tareas/pendientes", response_model=list)
async def tareas_pendientes_de_evento(
    evento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "leer")),
):
    evento = await obtener_evento(db, evento_id)
    if not evento or (
        current_user.id_rol != 1 and evento.id_hogar != current_user.id_hogar
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
        )
    return await listar_tareas_de_evento_por_estado(db, evento_id, "pendiente")


@router.get("/{evento_id}/tareas/completadas", response_model=list)
async def tareas_completadas_de_evento(
    evento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "leer")),
):
    evento = await obtener_evento(db, evento_id)
    if not evento or (
        current_user.id_rol != 1 and evento.id_hogar != current_user.id_hogar
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
        )
    return await listar_tareas_de_evento_por_estado(db, evento_id, "completada")


@router.get("/{evento_id}/miembros", response_model=list)
async def miembros_de_evento(
    evento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "leer")),
):
    evento = await obtener_evento(db, evento_id)
    if not evento or (
        current_user.id_rol != 1 and evento.id_hogar != current_user.id_hogar
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
        )
    return await miembros_relacionados_a_evento(db, evento_id)


@router.delete("/{evento_id}/tareas/{tarea_id}", response_model=dict)
async def remover_tarea_de_evento(
    evento_id: int,
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "actualizar")),
):
    evento = await obtener_evento(db, evento_id)
    if not evento or (
        current_user.id_rol != 1 and evento.id_hogar != current_user.id_hogar
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
        )

    tarea = await quitar_tarea_de_evento(db, evento_id, tarea_id)
    if not tarea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no pertenece al evento"
        )

    await db.commit()
    return {"mensaje": "Tarea removida del evento"}


@router.post("/{evento_id}/tareas/{tarea_id}", response_model=dict)
async def agregar_tarea_a_evento(
    evento_id: int,
    tarea_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "actualizar")),
):
    evento = await obtener_evento(db, evento_id)
    if not evento or (
        current_user.id_rol != 1 and evento.id_hogar != current_user.id_hogar
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
        )

    try:
        await asignar_tarea_a_evento(db, tarea_id, evento_id)
        await db.commit()
        return {"mensaje": "Tarea vinculada al evento"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno")


@router.put("/{evento_id}/tareas/{tarea_id}/miembro/{miembro_id}", response_model=dict)
async def reasignar_miembro_en_tarea_evento(
    evento_id: int,
    tarea_id: int,
    miembro_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Eventos", "actualizar")),
):
    evento = await obtener_evento(db, evento_id)
    if not evento or (
        current_user.id_rol != 1 and evento.id_hogar != current_user.id_hogar
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado"
        )
    try:
        await reasignar_miembro_tarea_evento(
            db, tarea_id, evento_id, miembro_id, current_user.id
        )
        await db.commit()
        return {"mensaje": "Miembro reasignado en la tarea del evento"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error interno")
