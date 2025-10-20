from sqlalchemy import Column, Integer, Text, DateTime, Boolean, ForeignKey, func
from db.database import Base

class Mensaje(Base):
    __tablename__ = "mensajes"
    
    id = Column(Integer, primary_key=True, index=True)
    id_hogar = Column(Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False)
    id_remitente = Column(Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False)
    contenido = Column(Text, nullable=False)
    fecha_envio = Column(DateTime, default=func.now())
    estado = Column(Boolean, default=True)