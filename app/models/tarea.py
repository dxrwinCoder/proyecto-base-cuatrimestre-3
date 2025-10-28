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


class Tarea(Base):
    __tablename__ = "tareas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(100), nullable=False)
    descripcion = Column(Text)
    categoria = Column(String(50), nullable=False)  # ej: "cocina", "salud"
    tipo_tarea = Column(String(50), nullable=False)  # ej: "compras", "supervision"
    fecha_limite = Column(Date, nullable=True)
    repeticion = Column(Enum("ninguna", "diaria", "semanal"), default="ninguna")
    estado_actual = Column(
        Enum("pendiente", "en_progreso", "completada", "cancelada"), default="pendiente"
    )
    asignado_a = Column(
        Integer, ForeignKey("miembros.id", ondelete="RESTRICT"), nullable=False
    )
    id_hogar = Column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )
    ubicacion = Column(String(50), nullable=True)
    id_sesion_mensaje = Column(
        String(100), nullable=True
    )  # ID de la conversación relacionada
    tiempo_total_segundos = Column(
        Integer, nullable=True
    )  # Tiempo desde asignación hasta completada
    id_evento = Column(
        Integer, ForeignKey("eventos.id", ondelete="SET NULL"), nullable=True
    )
    fecha_asignacion = Column(
        DateTime, default=func.now()
    )  # Momento en que se asignó la tarea
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    estado = Column(Boolean, default=True)
