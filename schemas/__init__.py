# schemas/__init__.py

# --- ¡PARCHE DE IMPORTACIÓN (SOLUCIÓN AL NameError)! ---

# 1. Importar todos los schemas base y los schemas referenciados
#    (El orden es importante)
from .rol import Rol, RolResponse
from .miembro import Miembro, MiembroBase, MiembroResponse
from .tarea import Tarea, TareaCreate, TareaUpdateEstado
from .comentario_tarea import ComentarioTarea, ComentarioTareaCreate
from .evento import Evento, EventoCreate
from .atributo import Atributo
from .atributo_miembro import AtributoMiembro
from .notificacion import Notificacion, NotificacionCreate
from .mensaje import Mensaje, MensajeCreate, MensajeResponse
from .modulo import Modulo
from .permiso import Permiso, PermisoCreate

# 2. Ahora que TODAS las clases están en el ámbito (scope),
#    podemos llamar a update_forward_refs() para las que tengan
#    referencias circulares (si aún las hay en string).

# Si MiembroResponse usa "RolResponse" (string) en lugar de RolResponse (clase):
MiembroResponse.update_forward_refs(RolResponse=RolResponse)

# Si Tarea usa "ComentarioTarea" (string):
# Tarea.update_forward_refs(ComentarioTarea=ComentarioTarea)

# Si Miembro usa "Mensaje" (string):
# Miembro.update_forward_refs(Mensaje=Mensaje)

# Nota: Si siguió el Parche 2 e importó 'RolResponse' directamente
# en 'miembro.py', es posible que esta línea ya no sea necesaria,
# pero no causará daño.
#MiembroResponse.update_forward_refs()
# --- FIN DEL PARCHE ---





# # schemas/__init__.py
# from .auth import Token, MiembroLogin, MiembroRegistro
# from .hogar import Hogar, HogarCreate
# from .miembro import Miembro, MiembroCreate, MiembroResponse
# from .modulo import Modulo, ModuloCreate
# from .permiso import Permiso, PermisoCreate, PermisoUpdate
# from .tarea import Tarea, TareaCreate
# from .rol import RolResponse

# # from .mensaje import Mensaje, MensajeCreate
# from .evento import Evento, EventoCreate

# # Reconstruir modelos para resolver referencias circulares
# MiembroResponse.model_rebuild()
