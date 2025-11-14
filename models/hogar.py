from sqlalchemy import Column, Integer, String, Boolean
from db.database import Base

class Hogar(Base):
    __tablename__ = "hogares"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    estado = Column(Boolean, default=True)