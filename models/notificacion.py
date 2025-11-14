# models/notificacion.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DATETIME, Text
from sqlalchemy.orm import relationship
from db.database import Base
from sqlalchemy.sql import func


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True)
    id_miembro_destino = Column(
        Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False
    )
    id_miembro_origen = Column(Integer, ForeignKey("miembros.id", ondelete="SET NULL"))
    id_tarea = Column(Integer, ForeignKey("tareas.id", ondelete="SET NULL"))

    # --- ¡PARCHE DE PRODUCCIÓN! (Columna faltante) ---
    id_evento = Column(Integer, ForeignKey("eventos.id", ondelete="SET NULL"))
    # --- FIN DEL PARCHE ---

    tipo = Column(String(50), nullable=False)
    mensaje = Column(Text, nullable=False)
    leido = Column(Boolean, default=False)
    fecha_creacion = Column(DATETIME, default=func.now())
    estado = Column(Integer, default=1)  # Asumiendo TINYINT como Integer

    # (Opcional, pero recomendado: relaciones)
    destinatario = relationship("Miembro", foreign_keys=[id_miembro_destino])
    origen = relationship("Miembro", foreign_keys=[id_miembro_origen])
    tarea = relationship("Tarea")
    evento = relationship("Evento")
