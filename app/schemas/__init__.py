# schemas/__init__.py
from .auth import Token, MiembroLogin, MiembroRegistro
from .hogar import Hogar, HogarCreate
from .miembro import Miembro, MiembroCreate
from .modulo import Modulo, ModuloCreate
from .permiso import Permiso, PermisoCreate, PermisoUpdate
from .tarea import Tarea, TareaCreate
#from .mensaje import Mensaje, MensajeCreate
from .evento import Evento, EventoCreate