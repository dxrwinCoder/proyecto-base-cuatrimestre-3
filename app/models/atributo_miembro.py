from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey
from db.database import Base


class AtributoMiembro(Base):
    __tablename__ = "atributo_miembro"

    id = Column(Integer, primary_key=True, index=True)
    id_miembro = Column(
        Integer, ForeignKey("miembros.id", ondelete="CASCADE"), nullable=False
    )
    id_atributo = Column(
        Integer, ForeignKey("atributos.id", ondelete="CASCADE"), nullable=False
    )
    valor = Column(Text, nullable=False)  # Valor almacenado como texto
    estado = Column(Boolean, default=True)
