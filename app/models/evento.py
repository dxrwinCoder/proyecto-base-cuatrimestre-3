from sqlalchemy import Column, Integer, String, Text, DateTime, Integer as IntCol, Boolean, ForeignKey
from db.database import Base

class Evento(Base):
    __tablename__ = "eventos"
    
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(100), nullable=False)
    descripcion = Column(Text)
    fecha_hora = Column(DateTime, nullable=False)
    duracion_min = Column(IntCol, default=60)
    id_hogar = Column(Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False)
    creado_por = Column(Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False)
    estado = Column(Boolean, default=True)