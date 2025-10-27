# schemas/__init__.py
from .auth import Token, MiembroLogin, MiembroRegistro
from .hogar import Hogar, HogarCreate
from .miembro import Miembro, MiembroCreate, MiembroResponse
from .modulo import Modulo, ModuloCreate
from .permiso import Permiso, PermisoCreate, PermisoUpdate
from .tarea import Tarea, TareaCreate
from .rol import RolResponse

# from .mensaje import Mensaje, MensajeCreate
from .evento import Evento, EventoCreate

# Reconstruir modelos para resolver referencias circulares
MiembroResponse.model_rebuild()
