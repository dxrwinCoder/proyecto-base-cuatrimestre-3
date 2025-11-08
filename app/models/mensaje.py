# models/mensaje.py
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DATETIME, Text
from db.database import Base
from sqlalchemy.sql import func  # Para los defaults de fecha


class Mensaje(Base):
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True)

    # --- ¡PARCHE "CALIBRADO"! (Cambié 'not_null' por 'nullable=False') ---
    id_hogar = Column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )
    id_remitente = Column(
        Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False
    )
    contenido = Column(Text, nullable=False)  # ¡Mejor 'Text' que 'String(500)'!
    # --- FIN DEL PARCHE ---

    fecha_envio = Column(DATETIME, default=func.now())
    leido = Column(Boolean, default=False)
    fecha_creacion = Column(DATETIME, default=func.now())
    fecha_actualizacion = Column(DATETIME, default=func.now(), onupdate=func.now())
    estado = Column(
        Integer, default=1
    )  # ¡Ojo! Su DB dice TINYINT, pero su código usa Integer

    # --- ¡LA RELACIÓN (Lado 1)! ---
    remitente = relationship("Miembro", back_populates="mensajes")
