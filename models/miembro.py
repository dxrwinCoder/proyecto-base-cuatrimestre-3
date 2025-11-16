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

    # --- Relaciones "Calibradas" ---

    # Relación con Rol (1-a-N, Miembro-Rol)
    rol = relationship("Rol", back_populates="miembros")

    # Relación con Hogar (1-a-N, Miembro-Hogar)
    # (Asumiendo que 'models/hogar.py' tiene: miembros = relationship("Miembro", ...))
    hogar = relationship("Hogar", back_populates="miembros")

    # Relación con Mensaje (N+1 Fix)
    mensajes = relationship(
        "Mensaje", back_populates="remitente", foreign_keys="[Mensaje.id_remitente]"
    )

    # Relación con Tarea (N+1 Fix)
    # (Asumiendo que 'models/tarea.py' tiene: miembro_asignado = relationship("Miembro", foreign_keys=[asignado_a]))
    tareas_asignadas = relationship(
        "Tarea", back_populates="miembro_asignado", foreign_keys="[Tarea.asignado_a]"
    )

    # Relación con Comentario (N+1 Fix)
    comentarios = relationship("ComentarioTarea", back_populates="miembro")
