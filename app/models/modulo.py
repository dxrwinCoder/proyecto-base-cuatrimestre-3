from sqlalchemy import Column, Integer, String, Text, Boolean
from db.database import Base

class Modulo(Base):
    __tablename__ = "modulos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)
    estado = Column(Boolean, default=True)