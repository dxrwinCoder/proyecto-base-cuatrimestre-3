
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.hogar import HogarCreate, Hogar
from services.hogar_service import crear_hogar, obtener_hogar, listar_hogares_activos
from utils.logger import setup_logger

logger = setup_logger("hogar_routes")

router = APIRouter(prefix="/hogares", tags=["Hogares"])

@router.post("/", response_model=Hogar)
async def crear_hogar_endpoint(hogar: HogarCreate, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Intentando crear hogar: {hogar.nombre}")
        resultado = await crear_hogar(db, hogar.nombre)
        logger.info(f"Hogar creado exitosamente: {resultado.nombre}")
        return resultado
    except Exception as e:
        logger.error(f"Error al crear hogar: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al crear hogar")

@router.get("/{hogar_id}", response_model=Hogar)
async def ver_hogar(hogar_id: int, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Buscando hogar con ID: {hogar_id}")
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
async def listar_hogares(db: AsyncSession = Depends(get_db)):
    try:
        logger.info("Listando hogares activos")
        hogares = await listar_hogares_activos(db)
        logger.info(f"Se encontraron {len(hogares)} hogares activos")
        return hogares
    except Exception as e:
        logger.error(f"Error al listar hogares: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al listar hogares")