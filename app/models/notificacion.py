from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    DateTime,
    func,
)
from db.database import Base


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    id_miembro_destino = Column(
        Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False
    )
    id_miembro_origen = Column(
        Integer, ForeignKey("miembros.id", ondelete="SET NULL"), nullable=True
    )
    id_tarea = Column(
        Integer, ForeignKey("tareas.id", ondelete="SET NULL"), nullable=True
    )
    id_evento = Column(
        Integer, ForeignKey("eventos.id", ondelete="SET NULL"), nullable=True
    )
    tipo = Column(String(50), nullable=False)  # ej: "cambio_estado_tarea"
    mensaje = Column(Text, nullable=False)
    leido = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=func.now())
    estado = Column(Boolean, default=True)
