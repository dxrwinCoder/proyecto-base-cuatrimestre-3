from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    func,
)
from db.database import Base


class ComentarioTarea(Base):
    __tablename__ = "comentarios_tarea"

    id = Column(Integer, primary_key=True, index=True)
    id_tarea = Column(
        Integer, ForeignKey("tareas.id", ondelete="CASCADE"), nullable=False
    )
    id_miembro = Column(
        Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False
    )
    contenido = Column(Text)
    url_imagen = Column(String(255), nullable=True)  # URL de imagen subida (opcional)
    fecha_creacion = Column(DateTime, default=func.now())
    estado = Column(Boolean, default=True)
