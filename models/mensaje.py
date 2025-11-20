# models/mensaje.py
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DATETIME, Text
from db.database import Base
from sqlalchemy.sql import func  # Para los defaults de fecha


class Mensaje(Base):
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True)

    id_hogar = Column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )
    id_remitente = Column(
        Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False
    )
    # Destinatario opcional para chat 1 a 1; si es None se interpreta como mensaje de hogar/broadcast.
    id_destinatario = Column(
        Integer, ForeignKey("miembros.id", ondelete="SET NULL"), nullable=True
    )
    contenido = Column(Text, nullable=False)

    fecha_envio = Column(DATETIME, default=func.now())
    leido = Column(Boolean, default=False)
    fecha_creacion = Column(DATETIME, default=func.now())
    fecha_actualizacion = Column(DATETIME, default=func.now(), onupdate=func.now())
    estado = Column(Integer, default=1)

    remitente = relationship(
        "Miembro", back_populates="mensajes", foreign_keys=[id_remitente]
    )
    destinatario = relationship(
        "Miembro",
        foreign_keys=[id_destinatario],
        post_update=True,
        overlaps="mensajes_recibidos",
    )
