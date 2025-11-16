from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    Enum,
    Boolean,
    ForeignKey,
    DateTime,
    func,
)
from db.database import Base
from sqlalchemy.orm import relationship


class Tarea(Base):
    __tablename__ = "tareas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(100), nullable=False)
    descripcion = Column(Text)
    categoria = Column(
        Enum("limpieza", "cocina", "compras", "mantenimiento"), nullable=False
    )
    fecha_limite = Column(Date, nullable=True)
    repeticion = Column(Enum("ninguna", "diaria", "semanal"), default="ninguna")
    estado_actual = Column(
        Enum("pendiente", "en_progreso", "completada"), default="pendiente"
    )
    asignado_a = Column(
        Integer, ForeignKey("miembros.id", ondelete="RESTRICT"), nullable=False
    )
    id_hogar = Column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )
    creado_por = Column(Integer, ForeignKey("miembros.id", ondelete="SET NULL"))
    ubicacion = Column(String(50), nullable=True)
    id_evento = Column(
        Integer, ForeignKey("eventos.id", ondelete="SET NULL"), nullable=True
    )
    id_sesion_mensaje = Column(String(100), nullable=True)
    tiempo_total_segundos = Column(Integer, nullable=True)
    fecha_asignacion = Column(DateTime, default=func.now())
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    estado = Column(Boolean, default=True)

    miembro_asignado = relationship("Miembro", foreign_keys=[asignado_a])
