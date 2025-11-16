# refactorizacion por gemini pro

from fastapi import APIRouter, Depends, HTTPException, status  # <-- ¡Añadir status!
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.hogar import HogarCreate, Hogar, HogarUpdate  # <-- ¡Importar HogarUpdate!
from services.hogar_service import (  # <-- ¡Importar todos los servicios!
    crear_hogar,
    obtener_hogar,
    listar_hogares_activos,
    actualizar_hogar,
    eliminar_hogar_logico,
)
from utils.logger import setup_logger

# --- ¡AÑADIR ESTAS IMPORTACIONES DE SEGURIDAD! ---
from models.miembro import Miembro
from utils.permissions import require_permission

# --- FIN DE IMPORTACIONES ---

logger = setup_logger("hogar_routes")

router = APIRouter(prefix="/hogares", tags=["Hogares"])


@router.post("/", response_model=Hogar, status_code=status.HTTP_201_CREATED)  # <-- 201
async def crear_hogar_endpoint(
    hogar: HogarCreate,
    db: AsyncSession = Depends(get_db),
    # --- ¡AÑADIR SEGURIDAD! ---
    current_user: Miembro = Depends(require_permission("Hogares", "crear")),
):
    try:
        logger.info(f"Intentando crear hogar: {hogar.nombre}")
        resultado = await crear_hogar(db, hogar)  # El servicio ya no hace commit

        await db.commit()  # <-- ¡LA RUTA HACE COMMIT!

        logger.info(f"Hogar creado exitosamente: {resultado.nombre}")
        return resultado
    except ValueError as e:  # Capturar el error de duplicado
        await db.rollback()
        logger.warning(f"Error de validación al crear hogar: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        await db.rollback()  # <-- ¡LA RUTA HACE ROLLBACK!
        logger.error(f"Error al crear hogar: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al crear hogar")


@router.get("/{hogar_id}", response_model=Hogar)
async def ver_hogar(
    hogar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Hogares", "leer")),
):
    try:
        logger.info(f"Buscando hogar con ID: {hogar_id}")

        # --- ¡ESTA ES LA LÓGICA QUE FALTABA! ---
        hogar = await obtener_hogar(db, hogar_id)
        if not hogar:
            logger.warning(f"Hogar no encontrado con ID: {hogar_id}")
            raise HTTPException(status_code=404, detail="Hogar no encontrado")

        logger.info(f"Hogar encontrado: {hogar.nombre}")
        return hogar

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al buscar hogar: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al buscar hogar")


@router.get("/", response_model=list[Hogar])
async def listar_hogares(
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Hogares", "leer")),
):
    """
    Ruta calibrada para listar todos los hogares activos.
    Devuelve una lista vacía [] si no hay hogares, en lugar de None.
    """
    try:
        logger.info("Listando hogares activos")

        # Esta es la lógica que faltaba y que previene el 'input: None'
        hogares = await listar_hogares_activos(db)

        logger.info(f"Se encontraron {len(hogares)} hogares activos")
        return hogares

    except Exception as e:
        logger.error(f"Error al listar hogares: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al listar hogares")


# --- ¡AÑADIR RUTAS DE ACTUALIZAR Y BORRAR (Buenas Prácticas)! ---
@router.patch("/{hogar_id}", response_model=Hogar)
async def actualizar_hogar_endpoint(
    hogar_id: int,
    hogar_data: HogarUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Hogares", "actualizar")),
):
    try:
        hogar_actualizado = await actualizar_hogar(db, hogar_id, hogar_data)
        if not hogar_actualizado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hogar no encontrado o inactivo",
            )

        await db.commit()
        print("commit realizado")
        return hogar_actualizado
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al actualizar hogar: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al actualizar hogar")


@router.delete("/{hogar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_hogar_endpoint(
    hogar_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Miembro = Depends(require_permission("Hogares", "eliminar")),
):
    try:
        resultado = await eliminar_hogar_logico(db, hogar_id)
        if not resultado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Hogar no encontrado"
            )

        await db.commit()
        return  # 204 No Content
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al eliminar hogar: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al eliminar hogar")


# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from db.database import get_db
# from schemas.hogar import HogarCreate, Hogar
# from services.hogar_service import crear_hogar, obtener_hogar, listar_hogares_activos
# from utils.logger import setup_logger
# from models.miembro import Miembro
# from utils.permissions import require_permission

# logger = setup_logger("hogar_routes")

# router = APIRouter(prefix="/hogares", tags=["Hogares"])


# @router.post("/", response_model=Hogar)
# async def crear_hogar_endpoint(
#     hogar: HogarCreate,
#     db: AsyncSession = Depends(get_db),
#     current_user: Miembro = Depends(require_permission("Hogares", "crear")),
# ):

#     try:
#         logger.info(f"Intentando crear hogar: {hogar.nombre}")
#         resultado = await crear_hogar(db, hogar.nombre)
#         logger.info(f"Hogar creado exitosamente: {resultado.nombre}")
#         return resultado
#     except Exception as e:
#         logger.error(f"Error al crear hogar: {str(e)}")
#         raise HTTPException(status_code=500, detail="Error interno al crear hogar")


# @router.get("/{hogar_id}", response_model=Hogar)
# async def ver_hogar(hogar_id: int, db: AsyncSession = Depends(get_db)):
#     try:
#         logger.info(f"Buscando hogar con ID: {hogar_id}")
#         hogar = await obtener_hogar(db, hogar_id)
#         if not hogar:
#             logger.warning(f"Hogar no encontrado con ID: {hogar_id}")
#             raise HTTPException(status_code=404, detail="Hogar no encontrado")
#         logger.info(f"Hogar encontrado: {hogar.nombre}")
#         return hogar
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error al buscar hogar: {str(e)}")
#         raise HTTPException(status_code=500, detail="Error interno al buscar hogar")


# @router.get("/", response_model=list[Hogar])
# async def listar_hogares(db: AsyncSession = Depends(get_db)):
#     try:
#         logger.info("Listando hogares activos")
#         hogares = await listar_hogares_activos(db)
#         logger.info(f"Se encontraron {len(hogares)} hogares activos")
#         return hogares
#     except Exception as e:
#         logger.error(f"Error al listar hogares: {str(e)}")
#         raise HTTPException(status_code=500, detail="Error interno al listar hogares")
