from sqlalchemy import Column, Integer, String, Text, Boolean
from db.database import Base


class Atributo(Base):
    __tablename__ = "atributos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(Text)
    tipo = Column(String(20), nullable=False)  # Ej: "INT", "VARCHAR", "BOOLEAN"
    estado = Column(Boolean, default=True)
