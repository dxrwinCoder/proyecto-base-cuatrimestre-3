# models/estadisticas_semanales.py
from sqlalchemy import (
    Column,
    Integer,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from db.database import (
    Base,
)  # Asegúrese de que 'Base' sea importada desde su archivo de base de datos


class EstadisticaSemanal(Base):
    """
    Modelo SQLAlchemy para la tabla 'estadisticas_semanales'.
    Almacena el recuento de tareas completadas por un miembro
    para una semana específica (definida por su día lunes).
    """

    __tablename__ = "estadisticas_semanales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_miembro = Column(
        Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False
    )

    # Columna 'inicio_semana' definida como DATE, según el DDL
    inicio_semana = Column(Date, nullable=False)

    tareas_completadas = Column(Integer, nullable=False, default=0)

    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_actualizacion = Column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # TINYINT(1) en MySQL se mapea a Boolean en SQLAlchemy
    estado = Column(Boolean, default=True)

    # Definición de la restricción Única (UNIQUE KEY) del DDL
    __table_args__ = (
        UniqueConstraint("id_miembro", "inicio_semana", name="uk_miembro_semana"),
    )

    # Relación para acceder al miembro desde una estadística
    miembro = relationship("Miembro")
