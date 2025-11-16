# schemas/ranking.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

# Importamos el schema de Miembro para anidarlo
from .miembro import MiembroResponse


class RankingEntry(BaseModel):
    # Usamos 'miembro' para anidar el objeto completo
    miembro: MiembroResponse
    tareas_completadas: int

    # --- ¡PARCHE DE SINTAXIS V1! ---
    # Calibrado para Pydantic 1.10.9 (compatible con Rasa/Spacy)
    class Config:
        orm_mode = True
