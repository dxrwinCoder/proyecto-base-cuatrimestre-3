from sqlalchemy import Column, Integer, Boolean, ForeignKey
from db.database import Base

class Permiso(Base):
    __tablename__ = "permisos"
    id = Column(Integer, primary_key=True, index=True)
    id_rol = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    id_modulo = Column(Integer, ForeignKey("modulos.id", ondelete="CASCADE"), nullable=False)
    puede_crear = Column(Boolean, default=False)
    puede_leer = Column(Boolean, default=True)
    puede_actualizar = Column(Boolean, default=False)
    puede_eliminar = Column(Boolean, default=False)
    estado = Column(Boolean, default=True)