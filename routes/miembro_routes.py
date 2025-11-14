from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.miembro import MiembroCreate, MiembroUpdate, Miembro, MiembroResponse
from services.miembro_service import (
    crear_miembro,
    obtener_miembro,
    listar_miembros_activos_por_hogar,
    actualizar_miembro,
    desactivar_miembro,
    obtener_todos_los_miembros,
    contar_miembros_por_hogar,
    obtener_miembros_por_rol,
)
from utils.logger import setup_logger
from utils.permissions import require_permission
from utils.auth import obtener_miembro_actual

logger = setup_logger("miembro_routes")

router = APIRouter(prefix="/miembros", tags=["Miembros"])


@router.post("/", response_model=MiembroResponse)
async def crear_miembro_endpoint(
    miembro: MiembroCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Miembros", "crear")),
):
    try:
        # Verificar que el usuario actual pertenece al mismo hogar o es administrador
        if current_user.id_rol != 1 and current_user.id_hogar != miembro.id_hogar:
            logger.warning(
                f"Intento no autorizado de crear miembro en hogar diferente: {miembro.id_hogar}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para crear miembros en este hogar",
            )

        logger.info(
            f"Intentando crear miembro: {miembro.nombre_completo} ({miembro.correo_electronico})"
        )
        resultado = await crear_miembro(db, miembro.model_dump())
        logger.info(f"Miembro creado exitosamente: {resultado.nombre_completo}")
        return resultado
    except ValueError as e:
        logger.warning(f"Error de validación al crear miembro: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear miembro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear miembro",
        )


@router.get("/todos", response_model=list[MiembroResponse])
async def obtener_todos_miembros(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Miembros", "leer")),
):
    try:
        logger.info("Solicitando lista de todos los miembros")
        miembros = await obtener_todos_los_miembros(db)
        return miembros
    except Exception as e:
        logger.error(f"Error al obtener todos los miembros: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener todos los miembros",
        )


@router.get("/{miembro_id}", response_model=MiembroResponse)
async def ver_miembro(
    miembro_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Miembros", "leer")),
):
    try:
        logger.info(f"Buscando miembro con ID: {miembro_id}")
        miembro = await obtener_miembro(db, miembro_id)

        if not miembro:
            logger.warning(f"Miembro no encontrado con ID: {miembro_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado"
            )

        # Verificar que el usuario actual puede ver este miembro
        if current_user.id_rol != 1 and current_user.id_hogar != miembro.id_hogar:
            logger.warning(
                f"Intento no autorizado de ver miembro de otro hogar: {miembro_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver este miembro",
            )

        logger.info(f"Miembro encontrado: {miembro.nombre_completo}")
        return miembro
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al buscar miembro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al buscar miembro",
        )


@router.get("/hogar/{hogar_id}", response_model=list[MiembroResponse])
async def listar_miembros_por_hogar(
    hogar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Miembros", "leer")),
):
    try:
        # Verificar que el usuario actual puede ver los miembros de este hogar
        if current_user.id_rol != 1 and current_user.id_hogar != hogar_id:
            logger.warning(
                f"Intento no autorizado de listar miembros de otro hogar: {hogar_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver los miembros de este hogar",
            )

        logger.info(f"Listando miembros activos para el hogar ID: {hogar_id}")
        miembros = await listar_miembros_activos_por_hogar(db, hogar_id)
        logger.info(
            f"Se encontraron {len(miembros)} miembros activos en el hogar {hogar_id}"
        )
        return miembros
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al listar miembros por hogar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al listar miembros por hogar",
        )


@router.patch("/{miembro_id}", response_model=MiembroResponse)
async def actualizar_miembro_endpoint(
    miembro_id: int,
    miembro_update: MiembroUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Miembros", "actualizar")),
):
    try:
        logger.info(f"Intentando actualizar miembro: {miembro_id}")
        miembro_actual = await obtener_miembro(db, miembro_id)

        if not miembro_actual:
            logger.warning(f"Miembro no encontrado para actualizar: {miembro_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado"
            )

        # Verificar permisos
        if (
            current_user.id_rol != 1
            and current_user.id_hogar != miembro_actual.id_hogar
        ):
            logger.warning(
                f"Intento no autorizado de actualizar miembro de otro hogar: {miembro_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para actualizar este miembro",
            )

        resultado = await actualizar_miembro(
            db, miembro_id, miembro_update.model_dump(exclude_unset=True)
        )
        logger.info(f"Miembro actualizado exitosamente: {miembro_id}")
        return resultado
    except ValueError as e:
        logger.warning(f"Error de validación al actualizar miembro: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar miembro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar miembro",
        )


@router.delete("/{miembro_id}")
async def eliminar_miembro_endpoint(
    miembro_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Miembros", "eliminar")),
):
    try:
        logger.info(f"Intentando eliminar miembro: {miembro_id}")
        miembro = await obtener_miembro(db, miembro_id)

        if not miembro:
            logger.warning(f"Miembro no encontrado para eliminar: {miembro_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado"
            )

        # Verificar permisos
        if current_user.id_rol != 1 and current_user.id_hogar != miembro.id_hogar:
            logger.warning(
                f"Intento no autorizado de eliminar miembro de otro hogar: {miembro_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para eliminar este miembro",
            )

        resultado = await desactivar_miembro(db, miembro_id)
        if resultado:
            logger.info(f"Miembro eliminado exitosamente: {miembro_id}")
            return {"message": "Miembro eliminado exitosamente"}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo eliminar el miembro",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar miembro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar miembro",
        )


@router.get("/hogar/{hogar_id}/cantidad", response_model=int)
async def cantidad_miembros_hogar(
    hogar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Miembros", "leer")),
):
    try:
        # Verificar que el usuario actual puede ver los miembros de este hogar
        if current_user.id_rol != 1 and current_user.id_hogar != hogar_id:
            logger.warning(
                f"Intento no autorizado de contar miembros de otro hogar: {hogar_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver los miembros de este hogar",
            )

        logger.info(f"Solicitando cantidad de miembros para el hogar: {hogar_id}")
        cantidad = await contar_miembros_por_hogar(db, hogar_id)
        return cantidad
    except Exception as e:
        logger.error(f"Error al contar miembros del hogar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al contar miembros del hogar",
        )


@router.get("/rol/{rol_id}", response_model=list[MiembroResponse])
async def miembros_por_rol(
    rol_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Miembros", "leer")),
):
    try:
        logger.info(f"Solicitando miembros con rol: {rol_id}")
        miembros = await obtener_miembros_por_rol(db, rol_id)
        return miembros
    except Exception as e:
        logger.error(f"Error al obtener miembros por rol: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al obtener miembros por rol",
        )
