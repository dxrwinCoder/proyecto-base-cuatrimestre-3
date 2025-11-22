from __future__ import annotations

from typing import Any, Dict, List, Optional, Text

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction

API_BASE = "http://127.0.0.1:8000"
BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10
TOKEN_METADATA_KEY = "jwt_token"


def _build_headers(token: Optional[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_metadata_token(tracker: Tracker) -> Optional[str]:
    return tracker.latest_message.get("metadata", {}).get(TOKEN_METADATA_KEY)


def api_get(path: str, params: Optional[Dict[str, Any]] = None, token: Optional[str] = None):
    try:
        response = requests.get(
            f"{API_BASE}{path}", params=params, headers=_build_headers(token), timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"error": "No se pudo conectar con el servidor."}


def api_post(path: str, body: Optional[Dict[str, Any]] = None, token: Optional[str] = None):
    try:
        response = requests.post(
            f"{API_BASE}{path}", json=body, headers=_build_headers(token), timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"error": "No se pudo conectar con el servidor."}


def api_put(path: str, body: Optional[Dict[str, Any]] = None, token: Optional[str] = None):
    try:
        response = requests.put(
            f"{API_BASE}{path}", json=body, headers=_build_headers(token), timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"error": "No se pudo conectar con el servidor."}


def api_delete(path: str, token: Optional[str] = None):
    try:
        response = requests.delete(
            f"{API_BASE}{path}", headers=_build_headers(token), timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"error": "No se pudo conectar con el servidor."}


class ValidateMemberCreationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_member_creation_form"

    async def validate_member_email(
        self,
        slot_value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if "@" in slot_value:
            return {"member_email": slot_value}
        dispatcher.utter_message(text="El correo no es válido. Intenta nuevamente.")
        return {"member_email": None}

    async def validate_member_role(
        self,
        slot_value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        valid_roles = ["1", "2"]
        if slot_value in valid_roles:
            return {"member_role": slot_value}
        dispatcher.utter_message(text="El rol debe ser 1 (Admin) o 2 (Hijo).")
        return {"member_role": None}

    async def validate_member_home(
        self,
        slot_value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if slot_value.isnumeric():
            return {"member_home": slot_value}
        dispatcher.utter_message(text="El ID del hogar debe ser numérico.")
        return {"member_home": None}


class ValidateMemberUpdateForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_member_update_form"

    async def validate_member_id(
        self,
        slot_value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if slot_value.isnumeric():
            return {"member_id": slot_value}
        dispatcher.utter_message(text="El ID del miembro debe ser numérico.")
        return {"member_id": None}


class ValidateCreateTaskCommentForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_create_task_comment_form"

    async def validate_task_id(
        self,
        slot_value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if slot_value.isnumeric():
            return {"task_id": slot_value}
        dispatcher.utter_message(text="El ID de la tarea debe ser numérico.")
        return {"task_id": None}

    async def validate_comment_image(
        self,
        slot_value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if slot_value and not slot_value.startswith("http"):
            dispatcher.utter_message(text="La URL debe iniciar con http o https.")
            return {"comment_image": None}
        return {"comment_image": slot_value}


class ValidateUpdateTaskCommentForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_update_task_comment_form"

    async def validate_comment_id(
        self,
        slot_value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if slot_value.isnumeric():
            return {"comment_id": slot_value}
        dispatcher.utter_message(text="El ID del comentario debe ser numérico.")
        return {"comment_id": None}


# ----------------------------
# ACCIONES PARA MIEMBRO
# ----------------------------


class ActionGetMemberTasks(Action):
    def name(self) -> Text:
        return "action_get_member_tasks"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        member_id = tracker.get_slot("member_id")
        token = _get_metadata_token(tracker)
        data = api_get(f"/tasks/member/{member_id}", token=token)
        if "error" in data:
            dispatcher.utter_message(data["error"])
            return []
        if not data:
            dispatcher.utter_message("No tienes tareas registradas.")
            return []
        msg = "Tus tareas:\n" + "\n".join(
            [f"• {t['title']} - {t['status']}" for t in data]
        )
        dispatcher.utter_message(msg)
        return []


class ActionCreateMemberTask(Action):
    def name(self) -> Text:
        return "action_create_member_task"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        member_id = tracker.get_slot("member_id")
        title = tracker.get_slot("task_title")
        description = tracker.get_slot("task_description")
        token = _get_metadata_token(tracker)
        body = {"member_id": member_id, "title": title, "description": description}
        data = api_post("/tasks", body, token=token)
        if "error" in data:
            dispatcher.utter_message(data["error"])
        else:
            dispatcher.utter_message(f"Tarea '{title}' creada correctamente.")
        return []


class ActionGetMemberEvents(Action):
    def name(self) -> Text:
        return "action_get_member_events"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        member_id = tracker.get_slot("member_id")
        token = _get_metadata_token(tracker)
        data = api_get(f"/events/member/{member_id}", token=token)
        if "error" in data:
            dispatcher.utter_message(data["error"])
            return []
        if not data:
            dispatcher.utter_message("No tienes eventos programados.")
            return []
        msg = "Tus eventos:\n" + "\n".join(
            [f"• {e['title']} - {e['date']}" for e in data]
        )
        dispatcher.utter_message(msg)
        return []


# ----------------------------
# ACCIONES PARA ADMINISTRADOR
# ----------------------------


class ActionAdminCreateTask(Action):
    def name(self) -> Text:
        return "action_admin_create_task"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        assigned_to = tracker.get_slot("assigned_to")
        title = tracker.get_slot("task_title")
        description = tracker.get_slot("task_description")
        token = _get_metadata_token(tracker)
        body = {
            "assigned_to": assigned_to,
            "title": title,
            "description": description,
        }
        data = api_post("/admin/tasks", body, token=token)
        if "error" in data:
            dispatcher.utter_message(data["error"])
        else:
            dispatcher.utter_message(f"Tarea asignada a {assigned_to} correctamente.")
        return []


class ActionAdminDeleteTask(Action):
    def name(self) -> Text:
        return "action_admin_delete_task"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        task_id = tracker.get_slot("task_id")
        token = _get_metadata_token(tracker)
        data = api_delete(f"/admin/tasks/{task_id}", token=token)
        if "error" in data:
            dispatcher.utter_message(data["error"])
        else:
            dispatcher.utter_message(f"Tarea {task_id} eliminada correctamente.")
        return []


class ActionAdminGetAllTasks(Action):
    def name(self) -> Text:
        return "action_admin_get_all_tasks"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        token = _get_metadata_token(tracker)
        data = api_get("/admin/tasks", token=token)
        if "error" in data:
            dispatcher.utter_message(data["error"])
            return []
        if not data:
            dispatcher.utter_message("No hay tareas registradas.")
            return []
        msg = "Tareas del hogar:\n" + "\n".join(
            [
                f"• {t['id']} - {t['title']} - {t['assigned_to']} - {t['status']}"
                for t in data
            ]
        )
        dispatcher.utter_message(msg)
        return []


class ActionAdminCreateEvent(Action):
    def name(self) -> Text:
        return "action_admin_create_event"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        title = tracker.get_slot("event_title")
        date = tracker.get_slot("event_date")
        description = tracker.get_slot("event_description")
        token = _get_metadata_token(tracker)
        body = {"title": title, "date": date, "description": description}
        data = api_post("/admin/events", body, token=token)
        if "error" in data:
            dispatcher.utter_message(data["error"])
        else:
            dispatcher.utter_message(f"Evento '{title}' creado correctamente.")
        return []


class ActionAdminDeleteEvent(Action):
    def name(self) -> Text:
        return "action_admin_delete_event"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        event_id = tracker.get_slot("event_id")
        token = _get_metadata_token(tracker)
        data = api_delete(f"/admin/events/{event_id}", token=token)
        if "error" in data:
            dispatcher.utter_message(data["error"])
        else:
            dispatcher.utter_message(f"Evento {event_id} eliminado.")
        return []


class ActionConfirmMemberCreated(Action):
    def name(self) -> Text:
        return "action_confirm_member_created"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Guardando el nuevo miembro en el hogar...")
        return []


class ActionConfirmMemberUpdated(Action):
    def name(self) -> Text:
        return "action_confirm_member_updated"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Actualizando la información del miembro...")
        return []


class ActionConfirmCommentCreated(Action):
    def name(self) -> Text:
        return "action_confirm_comment_created"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Registrando tu comentario...")
        return []


class ActionConfirmCommentUpdated(Action):
    def name(self) -> Text:
        return "action_confirm_comment_updated"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Aplicando los cambios al comentario...")
        return []


# ==============================================================================
# FORMULARIO: CREAR MIEMBRO
# ==============================================================================


class MemberCreationForm(Action):
    def name(self) -> Text:
        return "member_creation_form"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        nombre = tracker.get_slot("member_fullname")
        correo = tracker.get_slot("member_email")
        contrasena = tracker.get_slot("member_password")
        id_rol = tracker.get_slot("member_role")
        id_hogar = tracker.get_slot("member_home")
        token = _get_metadata_token(tracker)

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
            response = requests.post(
                f"{BASE_URL}/miembros/create",
                json=payload,
                headers=_build_headers(token),
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                dispatcher.utter_message(text="Miembro creado correctamente.")
            else:
                dispatcher.utter_message(text="No se pudo crear el miembro.")

        except Exception:
            dispatcher.utter_message(
                text="Error al conectar con el servidor FastAPI."
            )

        return []


# ==============================================================================
# FORMULARIO: ACTUALIZAR MIEMBRO
# ==============================================================================


class MemberUpdateForm(Action):
    def name(self) -> Text:
        return "member_update_form"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        member_id = tracker.get_slot("member_id")
        nombre = tracker.get_slot("member_fullname")
        correo = tracker.get_slot("member_email")
        id_rol = tracker.get_slot("member_role")
        token = _get_metadata_token(tracker)

        if not member_id:
            dispatcher.utter_message(text="Debes indicar el ID del miembro.")
            return []

        payload: Dict[str, Any] = {}
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
                f"{BASE_URL}/miembros/{member_id}/update",
                json=payload,
                headers=_build_headers(token),
                timeout=TIMEOUT,
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
    def name(self) -> Text:
        return "delete_member"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        member_id = tracker.get_slot("member_id")
        token = _get_metadata_token(tracker)

        if not member_id:
            dispatcher.utter_message(
                text="Debes indicar un ID de miembro para eliminarlo."
            )
            return []

        try:
            response = requests.delete(
                f"{BASE_URL}/miembros/{member_id}/delete",
                headers=_build_headers(token),
                timeout=TIMEOUT,
            )

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
    def name(self) -> Text:
        return "list_members"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        token = _get_metadata_token(tracker)
        try:
            response = requests.get(
                f"{BASE_URL}/miembros/list",
                headers=_build_headers(token),
                timeout=TIMEOUT,
            )

            if response.status_code != 200:
                dispatcher.utter_message(
                    text="No se pudo obtener la lista de miembros."
                )
                return []

            data = response.json()
            text = "Miembros registrados:\n\n"
            for member in data:
                text += (
                    f"- {member['id']}: {member['nombre_completo']} "
                    f"({member['correo_electronico']})\n"
                )

            dispatcher.utter_message(text=text)

        except Exception:
            dispatcher.utter_message(text="No fue posible conectar con el servidor.")

        return []


# ==============================================================================
# FORMULARIO: CREAR COMENTARIO EN TAREA
# ==============================================================================


class CreateTaskCommentForm(Action):
    def name(self) -> Text:
        return "create_task_comment_form"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        id_tarea = tracker.get_slot("task_id")
        id_miembro = tracker.get_slot("member_id")
        contenido = tracker.get_slot("comment_text")
        url_imagen = tracker.get_slot("comment_image")
        token = _get_metadata_token(tracker)

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
            response = requests.post(
                f"{BASE_URL}/comentarios/create",
                json=payload,
                headers=_build_headers(token),
                timeout=TIMEOUT,
            )

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
    def name(self) -> Text:
        return "update_task_comment_form"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        comment_id = tracker.get_slot("comment_id")
        contenido = tracker.get_slot("comment_text")
        url_imagen = tracker.get_slot("comment_image")
        token = _get_metadata_token(tracker)

        if not comment_id:
            dispatcher.utter_message(text="Debes indicar el ID del comentario.")
            return []

        payload: Dict[str, Any] = {}
        if contenido:
            payload["contenido"] = contenido
        if url_imagen:
            payload["url_imagen"] = url_imagen

        if not payload:
            dispatcher.utter_message(text="No se enviaron cambios para actualizar.")
            return []

        try:
            response = requests.put(
                f"{BASE_URL}/comentarios/{comment_id}/update",
                json=payload,
                headers=_build_headers(token),
                timeout=TIMEOUT,
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
    def name(self) -> Text:
        return "delete_comment"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        comment_id = tracker.get_slot("comment_id")
        token = _get_metadata_token(tracker)

        if not comment_id:
            dispatcher.utter_message(text="Indica el ID del comentario a eliminar.")
            return []

        try:
            response = requests.delete(
                f"{BASE_URL}/comentarios/{comment_id}/delete",
                headers=_build_headers(token),
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                dispatcher.utter_message(text="Comentario eliminado.")
            else:
                dispatcher.utter_message(text="No se pudo eliminar el comentario.")

        except Exception:
            dispatcher.utter_message(text="No fue posible conectar con FastAPI.")

        return []
