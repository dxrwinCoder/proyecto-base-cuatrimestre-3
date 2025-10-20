from sqlalchemy import Column, Integer, String, Text, Date, Enum, Boolean, ForeignKey
from db.database import Base

class Tarea(Base):
    __tablename__ = "tareas"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(100), nullable=False)
    descripcion = Column(Text)
    categoria = Column(Enum("limpieza", "cocina", "compras", "mantenimiento"), nullable=False)
    fecha_limite = Column(Date, nullable=True)
    repeticion = Column(Enum("ninguna", "diaria", "semanal"), default="ninguna")
    estado_tarea = Column(Enum("pendiente", "completada"), default="pendiente")
    asignado_a = Column(Integer, ForeignKey("miembros.id", ondelete="RESTRICT"), nullable=False)
    id_hogar = Column(Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False)
    ubicacion = Column(String(50), nullable=True)
    estado = Column(Boolean, default=True)