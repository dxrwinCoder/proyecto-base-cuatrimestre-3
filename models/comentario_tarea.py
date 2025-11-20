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
from sqlalchemy.orm import relationship
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
    contenido = Column(Text, nullable=False)
    # Se amplía a Text para permitir almacenar base64 si se desea
    url_imagen = Column(Text, nullable=True)  # puede almacenar ruta o base64
    fecha_creacion = Column(DateTime, default=func.now())
    estado = Column(Boolean, default=True)

    miembro = relationship("Miembro", back_populates="comentarios")
    tarea = relationship("Tarea", back_populates="comentarios")
