# models/tarea.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Boolean,
    DateTime,
    Text,
    Enum,
    Date,
    func,
)
from sqlalchemy.orm import relationship  # <-- ¡Asegúrese de importar relationship!
from db.database import Base


class Tarea(Base):
    __tablename__ = "tareas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(100), nullable=False)
    descripcion = Column(Text)
    categoria = Column(
        Enum("limpieza", "cocina", "compras", "mantenimiento"), nullable=False
    )
    fecha_limite = Column(Date, nullable=True)
    repeticion = Column(
        Enum("ninguna", "diaria", "semanal"), nullable=False, default="ninguna"
    )
    estado_actual = Column(String(20), nullable=False, default="pendiente")

    asignado_a = Column(
        Integer, ForeignKey("miembros.id", ondelete="RESTRICT"), nullable=False
    )
    id_hogar = Column(
        Integer, ForeignKey("hogares.id", ondelete="CASCADE"), nullable=False
    )

    # Columna "Calibrada" (para cumplir Caso de Uso 'Notificar al creador')
    creado_por = Column(Integer, ForeignKey("miembros.id", ondelete="SET NULL"))

    ubicacion = Column(String(50), nullable=True)
    fecha_asignacion = Column(DateTime, default=func.now())
    tiempo_total_segundos = Column(Integer, nullable=True)
    id_evento = Column(Integer, ForeignKey("eventos.id", ondelete="SET NULL"))
    id_sesion_mensaje = Column(String(255), nullable=True, unique=True)
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    estado = Column(Boolean, default=True)  # TINYINT es Boolean

    # --- ¡INICIO DEL PARCHE DE SOLUCIÓN! ---

    # Relación para 'asignado_a' (evita N+1 en Rasa)
    miembro_asignado = relationship(
        "Miembro", foreign_keys=[asignado_a], back_populates="tareas_asignadas"
    )

    # Relación para 'creado_por' (soluciona el MapperError)
    creador = relationship(
        "Miembro", foreign_keys=[creado_por], back_populates="tareas_creadas"
    )

    # Relación con 'comentarios_tarea' (soluciona el MapperError anterior)
    comentarios = relationship(
        "ComentarioTarea", back_populates="tarea", cascade="all, delete-orphan"
    )

    # (Opcional: relación con evento)
    evento = relationship("Evento")

    # --- FIN DEL PARCHE ---
