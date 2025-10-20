
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.miembro import MiembroCreate, Miembro
from services.miembro_service import crear_miembro, obtener_miembro, listar_miembros_activos_por_hogar
from utils.logger import setup_logger

logger = setup_logger("miembro_routes")

router = APIRouter(prefix="/miembros", tags=["Miembros"])

@router.post("/", response_model=Miembro)
async def crear_miembro_endpoint(miembro: MiembroCreate, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Intentando crear miembro: {miembro.nombre_completo} ({miembro.correo_electronico})")
        resultado = await crear_miembro(db, miembro.model_dump())
        logger.info(f"Miembro creado exitosamente: {resultado.nombre_completo}")
        return resultado
    except Exception as e:
        logger.error(f"Error al crear miembro: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al crear miembro")

@router.get("/{miembro_id}", response_model=Miembro)
async def ver_miembro(miembro_id: int, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Buscando miembro con ID: {miembro_id}")
        miembro = await obtener_miembro(db, miembro_id)
        if not miembro:
            logger.warning(f"Miembro no encontrado con ID: {miembro_id}")
            raise HTTPException(status_code=404, detail="Miembro no encontrado")
        logger.info(f"Miembro encontrado: {miembro.nombre_completo}")
        return miembro
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al buscar miembro: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al buscar miembro")

@router.get("/hogar/{hogar_id}", response_model=list[Miembro])
async def listar_miembros_por_hogar(hogar_id: int, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Listando miembros activos para el hogar ID: {hogar_id}")
        miembros = await listar_miembros_activos_por_hogar(db, hogar_id)
        logger.info(f"Se encontraron {len(miembros)} miembros activos en el hogar {hogar_id}")
        return miembros
    except Exception as e:
        logger.error(f"Error al listar miembros por hogar: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al listar miembros por hogar")