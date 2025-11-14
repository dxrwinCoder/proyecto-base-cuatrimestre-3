from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from db.database import Base


class Miembro(Base):
    __tablename__ = "miembros"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(100), nullable=False)
    correo_electronico = Column(String(150), unique=True, nullable=False)
    contrasena_hash = Column(String(255), nullable=False)
    id_rol = Column(Integer, ForeignKey("roles.id"), nullable=False)
    id_hogar = Column(Integer, ForeignKey("hogares.id"), nullable=False)
    estado = Column(Boolean, default=True)
    fecha_creacion = Column(
        DateTime, server_default=func.now()
    )  # Usar func.now() para que MySQL maneje el valor
    fecha_actualizacion = Column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relación con la tabla roles
    rol = relationship("Rol", back_populates="miembros")

    id = Column(Integer, primary_key=True)
    # ... (El resto de sus columnas: nombre_completo, correo_electronico, etc.)

    # --- ¡AÑADA ESTA LÍNEA (Lado 2 del N+1)! ---
    mensajes = relationship(
        "Mensaje", back_populates="remitente", foreign_keys="[Mensaje.id_remitente]"
    )
