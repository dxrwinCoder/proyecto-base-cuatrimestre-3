from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, func
from sqlalchemy.orm import relationship
from db.database import Base

class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    estado = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())  # Usar func.now() para que MySQL maneje el valor
    fecha_actualizacion = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relación con la tabla miembros
    miembros = relationship("Miembro", back_populates="rol")