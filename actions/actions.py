import requests
from typing import Any, Dict, Text, List
from rasa_sdk import Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from typing import Dict, Text, Any
from rasa_sdk import FormValidationAction
from rasa_sdk.types import DomainDict

API_BASE = "http://127.0.0.1:8000"
TIMEOUT = 10


def _auth_headers(tracker) -> Dict[str, str]:
    """
    Obtiene el token JWT adjuntado en metadata o slot 'token' para construir el header Authorization.
    """
    meta = tracker.latest_message.get("metadata", {}) if tracker and tracker.latest_message else {}
    token = meta.get("token") or tracker.get_slot("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_get(path: str, tracker, params: Dict = None):
    try:
        r = requests.get(
            f"{API_BASE}{path}",
            params=params,
            headers=_auth_headers(tracker),
            timeout=TIMEOUT,
        )
        return r
    except Exception:
        return None


def api_post(path: str, tracker, body: Dict = None):
    try:
        r = requests.post(
            f"{API_BASE}{path}",
            json=body,
            headers=_auth_headers(tracker),
            timeout=TIMEOUT,
        )
        return r
    except Exception:
        return None


def api_put(path: str, tracker, body: Dict = None):
    try:
        r = requests.put(
            f"{API_BASE}{path}",
            json=body,
            headers=_auth_headers(tracker),
            timeout=TIMEOUT,
        )
        return r
    except Exception:
        return None


def api_delete(path: str, tracker):
    try:
        r = requests.delete(
            f"{API_BASE}{path}", headers=_auth_headers(tracker), timeout=TIMEOUT
        )
        return r
    except Exception:
        return None


class ValidateMemberCreationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_member_creation_form"

    async def validate_member_email(
        self, slot_value, dispatcher, tracker, domain
    ) -> Dict[Text, Any]:
        if "@" in slot_value:
            return {"member_email": slot_value}
        dispatcher.utter_message(text="El correo no es válido. Intenta nuevamente.")
        return {"member_email": None}

    async def validate_member_role(self, slot_value, dispatcher, tracker, domain):
        valid_roles = ["1", "2"]
        if slot_value in valid_roles:
            return {"member_role": slot_value}
        dispatcher.utter_message(text="El rol debe ser 1 (Admin) o 2 (Hijo).")
        return {"member_role": None}

    async def validate_member_home(self, slot_value, dispatcher, tracker, domain):
        if slot_value.isnumeric():
            return {"member_home": slot_value}
        dispatcher.utter_message(text="El ID del hogar debe ser numérico.")
        return {"member_home": None}


class ValidateMemberUpdateForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_member_update_form"

    async def validate_member_id(self, slot_value, dispatcher, tracker, domain):
        if slot_value.isnumeric():
            return {"member_id": slot_value}
        dispatcher.utter_message(text="El ID del miembro debe ser numérico.")
        return {"member_id": None}


class ValidateCreateTaskCommentForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_create_task_comment_form"

    async def validate_task_id(self, slot_value, dispatcher, tracker, domain):
        if slot_value.isnumeric():
            return {"task_id": slot_value}
        dispatcher.utter_message(text="El ID de la tarea debe ser numérico.")
        return {"task_id": None}

    async def validate_comment_image(self, slot_value, dispatcher, tracker, domain):
        if slot_value and not slot_value.startswith("http"):
            dispatcher.utter_message(text="La URL debe iniciar con http o https.")
            return {"comment_image": None}
        return {"comment_image": slot_value}


class ValidateUpdateTaskCommentForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_update_task_comment_form"

    async def validate_comment_id(self, slot_value, dispatcher, tracker, domain):
        return {"comment_id": slot_value if slot_value.isnumeric() else None}


# ----------------------------
# ACCIONES PARA MIEMBRO
# ----------------------------


class ActionGetMemberTasks(Action):
    def name(self) -> Text:
        return "action_get_member_tasks"

    def run(self, dispatcher, tracker, domain):
        resp = api_get("/tareas/mias/", tracker)
        if not resp or resp.status_code != 200:
            dispatcher.utter_message("No se pudo obtener tus tareas.")
            return []
        data = resp.json()
        if not data:
            dispatcher.utter_message("No tienes tareas registradas.")
            return []
        msg = "Tus tareas:" + "".join(
            [f"\n• {t['titulo']} - {t['estado_actual']}" for t in data]
        )
        dispatcher.utter_message(msg)
        return []


class ActionCreateMemberTask(Action):
    def name(self) -> Text:
        return "action_create_member_task"

    def run(self, dispatcher, tracker, domain):
        titulo = tracker.get_slot("task_title")
        descripcion = tracker.get_slot("task_description")
        asignado_a = tracker.get_slot("member_id")
        meta = tracker.latest_message.get("metadata", {}) if tracker.latest_message else {}
        id_hogar = meta.get("id_hogar")

        if not (titulo and asignado_a and id_hogar):
            dispatcher.utter_message("Faltan datos para crear la tarea (título, asignado, hogar).")
            return []

        body = {
            "titulo": titulo,
            "descripcion": descripcion,
            "categoria": "limpieza",
            "repeticion": "ninguna",
            "asignado_a": int(asignado_a),
            "id_hogar": int(id_hogar),
        }
        resp = api_post("/tareas/", tracker, body)
        if not resp or resp.status_code != 201:
            dispatcher.utter_message("No se pudo crear la tarea.")
        else:
            dispatcher.utter_message(f"Tarea '{titulo}' creada correctamente.")
        return []


class ActionGetMemberEvents(Action):
    def name(self) -> Text:
        return "action_get_member_events"

    def run(self, dispatcher, tracker, domain):
        meta = tracker.latest_message.get("metadata", {}) if tracker.latest_message else {}
        id_hogar = meta.get("id_hogar")
        if not id_hogar:
            dispatcher.utter_message("No pude identificar tu hogar.")
            return []
        resp = api_get(f"/eventos/hogar/{id_hogar}", tracker)
        if not resp or resp.status_code != 200:
            dispatcher.utter_message("No se pudieron obtener los eventos.")
            return []
        data = resp.json()
        if not data:
            dispatcher.utter_message("No tienes eventos programados.")
            return []
        msg = "Tus eventos:" + "".join([f"\n• {e['titulo']} - {e['fecha_hora']}" for e in data])
        dispatcher.utter_message(msg)
        return []


# ----------------------------
# ACCIONES PARA ADMINISTRADOR
# ----------------------------


class ActionAdminCreateTask(Action):
    def name(self) -> Text:
        return "action_admin_create_task"

    def run(self, dispatcher, tracker, domain):
        asignado_a = tracker.get_slot("assigned_to")
        titulo = tracker.get_slot("task_title")
        descripcion = tracker.get_slot("task_description")
        meta = tracker.latest_message.get("metadata", {}) if tracker.latest_message else {}
        id_hogar = meta.get("id_hogar")
        if not (asignado_a and titulo and id_hogar):
            dispatcher.utter_message("Faltan datos para asignar la tarea (destinatario, título, hogar).")
            return []
        body = {
            "titulo": titulo,
            "descripcion": descripcion,
            "categoria": "limpieza",
            "repeticion": "ninguna",
            "asignado_a": int(asignado_a),
            "id_hogar": int(id_hogar),
        }
        resp = api_post("/tareas/", tracker, body)
        if not resp or resp.status_code != 201:
            dispatcher.utter_message("No se pudo crear la tarea.")
        else:
            dispatcher.utter_message(f"Tarea asignada a {asignado_a} correctamente.")
        return []


class ActionAdminDeleteTask(Action):
    def name(self) -> Text:
        return "action_admin_delete_task"

    def run(self, dispatcher, tracker, domain):
        task_id = tracker.get_slot("task_id")
        if not task_id:
            dispatcher.utter_message("Debes indicar el ID de la tarea.")
            return []
        resp = api_delete(f"/tareas/{task_id}", tracker)
        if not resp or resp.status_code not in (200, 204):
            dispatcher.utter_message("No se pudo eliminar la tarea.")
        else:
            dispatcher.utter_message(f"Tarea {task_id} eliminada correctamente.")
        return []


class ActionAdminGetAllTasks(Action):
    def name(self) -> Text:
        return "action_admin_get_all_tasks"

    def run(self, dispatcher, tracker, domain):
        resp = api_get("/tareas/hogar/todas", tracker)
        if not resp or resp.status_code != 200:
            dispatcher.utter_message("No se pudieron obtener las tareas.")
            return []
        data = resp.json()
        if not data:
            dispatcher.utter_message("No hay tareas registradas.")
            return []
        msg = "Tareas del hogar:" + "".join(
            [f"\n• {t['id']} - {t['titulo']} - {t['estado_actual']}" for t in data]
        )
        dispatcher.utter_message(msg)
        return []


class ActionAdminCreateEvent(Action):
    def name(self) -> Text:
        return "action_admin_create_event"

    def run(self, dispatcher, tracker, domain):
        titulo = tracker.get_slot("event_title")
        fecha = tracker.get_slot("event_date")
        descripcion = tracker.get_slot("event_description")
        meta = tracker.latest_message.get("metadata", {}) if tracker.latest_message else {}
        id_hogar = meta.get("id_hogar")
        creado_por = meta.get("id_miembro")

        if not (titulo and fecha and id_hogar and creado_por):
            dispatcher.utter_message("Faltan datos para crear el evento (título, fecha, hogar).")
            return []

        body = {
            "titulo": titulo,
            "descripcion": descripcion,
            "fecha_hora": fecha,
            "duracion_min": 60,
            "id_hogar": int(id_hogar),
            "creado_por": int(creado_por),
        }
        resp = api_post("/eventos/", tracker, body)
        if not resp or resp.status_code != 201:
            dispatcher.utter_message("No se pudo crear el evento.")
        else:
            dispatcher.utter_message(f"Evento '{titulo}' creado correctamente.")
        return []


class ActionAdminDeleteEvent(Action):
    def name(self) -> Text:
        return "action_admin_delete_event"

    def run(self, dispatcher, tracker, domain):
        event_id = tracker.get_slot("event_id")
        if not event_id:
            dispatcher.utter_message("Debes indicar el ID del evento.")
            return []
        resp = api_delete(f"/eventos/{event_id}", tracker)
        if not resp or resp.status_code not in (200, 204):
            dispatcher.utter_message("No se pudo eliminar el evento.")
        else:
            dispatcher.utter_message(f"Evento {event_id} eliminado.")
        return []


# ==============================================================================
# FORMULARIO: CREAR MIEMBRO
# ==============================================================================


class MemberCreationForm(Action):

    def name(self):
        return "member_creation_form"

    async def run(self, dispatcher, tracker, domain):

        nombre = tracker.get_slot("member_fullname")
        correo = tracker.get_slot("member_email")
        contrasena = tracker.get_slot("member_password")
        id_rol = tracker.get_slot("member_role")
        id_hogar = tracker.get_slot("member_home")

        missing = []
        if not nombre:
            missing.append("nombre completo")
        if not correo:
            missing.append("correo electrónico")
        if not contrasena:
            missing.append("contraseña")
        if not id_rol:
            missing.append("rol")
        if not id_hogar:
            missing.append("hogar")

        if missing:
            dispatcher.utter_message(text=f"Faltan datos: {', '.join(missing)}")
            return []

        payload = {
            "nombre_completo": nombre,
            "correo_electronico": correo,
            "password": contrasena,
            "id_rol": int(id_rol),
            "id_hogar": int(id_hogar),
        }

        try:
            response = requests.post(f"{BASE_URL}/miembros/create", json=payload)

            if response.status_code == 200:
                dispatcher.utter_message(text="Miembro creado correctamente.")
            else:
                dispatcher.utter_message(text="No se pudo crear el miembro.")

        except Exception:
            dispatcher.utter_message(text="Error al conectar con el servidor FastAPI.")

        return []


# ==============================================================================
# FORMULARIO: ACTUALIZAR MIEMBRO
# ==============================================================================


class MemberUpdateForm(Action):

    def name(self):
        return "member_update_form"

    async def run(self, dispatcher, tracker, domain):

        member_id = tracker.get_slot("member_id")
        nombre = tracker.get_slot("member_fullname")
        correo = tracker.get_slot("member_email")
        id_rol = tracker.get_slot("member_role")

        if not member_id:
            dispatcher.utter_message(text="Debes indicar el ID del miembro.")
            return []

        payload = {}
        if nombre:
            payload["nombre_completo"] = nombre
        if correo:
            payload["correo_electronico"] = correo
        if id_rol:
            payload["id_rol"] = int(id_rol)

        if not payload:
            dispatcher.utter_message(text="No se proporcionaron datos para actualizar.")
            return []

        try:
            response = requests.put(
                f"{BASE_URL}/miembros/{member_id}/update", json=payload
            )

            if response.status_code == 200:
                dispatcher.utter_message(text="Miembro actualizado correctamente.")
            else:
                dispatcher.utter_message(text="No se pudo actualizar el miembro.")

        except Exception:
            dispatcher.utter_message(text="Error al conectar con el servidor FastAPI.")

        return []


# ==============================================================================
# ACCIÓN: ELIMINAR MIEMBRO
# ==============================================================================


class DeleteMember(Action):

    def name(self):
        return "delete_member"

    async def run(self, dispatcher, tracker, domain):

        member_id = tracker.get_slot("member_id")

        if not member_id:
            dispatcher.utter_message(
                text="Debes indicar un ID de miembro para eliminarlo."
            )
            return []

        try:
            response = requests.delete(f"{BASE_URL}/miembros/{member_id}/delete")

            if response.status_code == 200:
                dispatcher.utter_message(text="Miembro eliminado exitosamente.")
            else:
                dispatcher.utter_message(text="No se logró eliminar el miembro.")

        except Exception:
            dispatcher.utter_message(text="Error al conectar con FastAPI.")

        return []


# ==============================================================================
# ACCIÓN: LISTAR MIEMBROS
# ==============================================================================


class ListMembers(Action):

    def name(self):
        return "list_members"

    async def run(self, dispatcher, tracker, domain):

        try:
            response = requests.get(f"{BASE_URL}/miembros/list")

            if response.status_code != 200:
                dispatcher.utter_message(
                    text="No se pudo obtener la lista de miembros."
                )
                return []

            data = response.json()
            text = "Miembros registrados:\n\n"
            for m in data:
                text += (
                    f"- {m['id']}: {m['nombre_completo']} ({m['correo_electronico']})\n"
                )

            dispatcher.utter_message(text=text)

        except:
            dispatcher.utter_message(text="No fue posible conectar con el servidor.")

        return []


# ==============================================================================
# FORMULARIO: CREAR COMENTARIO EN TAREA
# ==============================================================================


class CreateTaskCommentForm(Action):

    def name(self):
        return "create_task_comment_form"

    async def run(self, dispatcher, tracker, domain):

        id_tarea = tracker.get_slot("task_id")
        id_miembro = tracker.get_slot("member_id")
        contenido = tracker.get_slot("comment_text")
        url_imagen = tracker.get_slot("comment_image")

        if not id_tarea or not id_miembro or not contenido:
            dispatcher.utter_message(text="Faltan datos para crear el comentario.")
            return []

        payload = {
            "id_tarea": int(id_tarea),
            "id_miembro": int(id_miembro),
            "contenido": contenido,
            "url_imagen": url_imagen,
        }

        try:
            response = requests.post(f"{BASE_URL}/comentarios/create", json=payload)

            if response.status_code == 200:
                dispatcher.utter_message(text="Comentario creado correctamente.")
            else:
                dispatcher.utter_message(text="No se pudo crear el comentario.")

        except Exception:
            dispatcher.utter_message(text="Error al conectar con FastAPI.")

        return []


# ==============================================================================
# FORMULARIO: ACTUALIZAR COMENTARIO
# ==============================================================================


class UpdateTaskCommentForm(Action):

    def name(self):
        return "update_task_comment_form"

    async def run(self, dispatcher, tracker, domain):

        comment_id = tracker.get_slot("comment_id")
        contenido = tracker.get_slot("comment_text")
        url_imagen = tracker.get_slot("comment_image")

        if not comment_id:
            dispatcher.utter_message(text="Debes indicar el ID del comentario.")
            return []

        payload = {}
        if contenido:
            payload["contenido"] = contenido
        if url_imagen:
            payload["url_imagen"] = url_imagen

        if not payload:
            dispatcher.utter_message(text="No se enviaron cambios para actualizar.")
            return []

        try:
            response = requests.put(
                f"{BASE_URL}/comentarios/{comment_id}/update", json=payload
            )

            if response.status_code == 200:
                dispatcher.utter_message(text="Comentario actualizado.")
            else:
                dispatcher.utter_message(text="No se pudo actualizar el comentario.")

        except Exception:
            dispatcher.utter_message(text="Error al conectar con FastAPI.")

        return []


# ==============================================================================
# ACCIÓN: ELIMINAR COMENTARIO
# ==============================================================================


class DeleteComment(Action):

    def name(self):
        return "delete_comment"

    async def run(self, dispatcher, tracker, domain):

        comment_id = tracker.get_slot("comment_id")

        if not comment_id:
            dispatcher.utter_message(text="Indica el ID del comentario a eliminar.")
            return []

        try:
            response = requests.delete(f"{BASE_URL}/comentarios/{comment_id}/delete")

            if response.status_code == 200:
                dispatcher.utter_message(text="Comentario eliminado.")
            else:
                dispatcher.utter_message(text="No se pudo eliminar el comentario.")

        except:
            dispatcher.utter_message(text="No fue posible conectar con FastAPI.")

        return []
