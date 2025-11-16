# actions/actions.py
import jwt
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

# --- 1. IMPORTACIONES DE SU PROYECTO FASTAPI ---
try:
    from db.database import AsyncSessionLocal
    from models.miembro import Miembro
    from models.tarea import Tarea
    from models.comentario_tarea import ComentarioTarea
    from models.rol import Rol
    from schemas.tarea import TareaCreate
    from schemas.comentario_tarea import ComentarioTareaCreate

    # Importar los servicios "calibrados"
    from services.tarea_service import (
        listar_tareas_por_miembro,
        obtener_tarea_por_id,
        actualizar_estado_tarea,
        agregar_comentario_a_tarea,
        crear_tarea as svc_crear_tarea,
    )
    from services.ranking_service import obtener_ranking_hogar
    from services.miembro_service import (
        listar_miembros_activos_por_hogar,
        obtener_miembro_por_nombre,
        listar_tareas_por_estado_y_hogar,
    )

except ImportError as e:
    print(f"\n[ERROR DE ACCIÓN RASA] Faltan importaciones: {e}")
    print(
        "Asegúrese de ejecutar 'rasa run actions' desde la raíz 'app/' y que todos los servicios existan."
    )
    exit(1)

# --- 2. CONFIGURACIÓN DE JWT Y SESIÓN DE BD ---
SECRET_KEY = "supersecretkey"  # ¡Debe coincidir con su .env!
ALGORITHM = "HS256"


def get_db_session() -> AsyncSession:
    """Crea una nueva sesión asíncrona de SQLAlchemy."""
    return AsyncSessionLocal()


async def get_miembro_from_tracker(
    tracker: Tracker, db: AsyncSession
) -> Miembro | None:
    """Decodifica el token JWT y obtiene el Miembro con su Rol."""
    metadata = tracker.get_slot("session_started_metadata") or {}
    token = metadata.get("token")
    if not token:
        print("[ERROR DE ACCIÓN RASA] No se recibió token en 'metadata'.")
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        miembro_id = payload.get("sub")

        stmt = (
            select(Miembro)
            .options(joinedload(Miembro.rol))
            .where(Miembro.id == int(miembro_id))
        )
        miembro = (await db.execute(stmt)).scalar_one_or_none()

        if not miembro:
            print(f"[ERROR DE ACCIÓN RASA] Miembro ID {miembro_id} no encontrado.")
            return None
        print(
            f"[INFO DE ACCIÓN RASA] Miembro autenticado: {miembro.correo_electronico} (Rol: {miembro.rol.nombre})"
        )
        return miembro
    except Exception as e:
        print(f"[ERROR DE ACCIÓN RASA] Error de autenticación/BD: {e}")
        return None


# --- 3. ACCIONES DE USUARIO Y GENERALES ---


class ActionConsultarMisTareas(Action):
    def name(self) -> Text:
        return "action_consultar_mis_tareas"

    async def run(self, dispatcher, tracker, domain):
        db = get_db_session()
        try:
            miembro = await get_miembro_from_tracker(tracker, db)
            if not miembro:
                dispatcher.utter_message(response="utter_error_accion")
                return []

            tareas = await listar_tareas_por_miembro(db, miembro.id)
            if not tareas:
                dispatcher.utter_message(
                    text=f"¡Buenas noticias, {miembro.nombre_completo}! No tienes ninguna tarea pendiente. ¡A disfrutar!"
                )
            else:
                response_text = f"¡Hola {miembro.nombre_completo}! Tienes {len(tareas)} tarea(s) pendiente(s). ¡Manos a la obra!\n"
                for i, tarea in enumerate(tareas):
                    response_text += f"\n{i+1}. *{tarea.titulo}* (Categoría: {tarea.categoria}, ID: {tarea.id})"
                dispatcher.utter_message(text=response_text)
        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
        return []


class ActionMarcarTareaCompletada(Action):
    def name(self) -> Text:
        return "action_marcar_tarea_completada"

    async def run(self, dispatcher, tracker, domain):
        db = get_db_session()
        try:
            miembro = await get_miembro_from_tracker(tracker, db)
            if not miembro:
                dispatcher.utter_message(response="utter_error_accion")
                return []

            tarea_nombre = next(tracker.get_latest_entity_values("tarea_nombre"), None)
            if not tarea_nombre:
                dispatcher.utter_message(
                    text="¿Qué tarea deseas marcar como completada? (Dime el nombre)"
                )
                return []

            stmt = select(Tarea).where(
                Tarea.titulo.ilike(
                    f"%{tarea_nombre}%"
                ),  # Usar 'ilike' para no ser sensible a mayúsculas
                Tarea.asignado_a == miembro.id,
                Tarea.estado_actual != "completada",
            )
            tarea = (await db.execute(stmt)).scalars().first()

            if not tarea:
                dispatcher.utter_message(
                    text=f"Lo siento, no encontré una tarea pendiente llamada '{tarea_nombre}' que esté asignada a ti."
                )
                return []

            try:
                await actualizar_estado_tarea(db, tarea.id, "completada", miembro.id)
                await db.commit()
                dispatcher.utter_message(
                    text=f"¡Excelente trabajo, {miembro.nombre_completo}! He marcado la tarea '{tarea.titulo}' como completada. 🥳"
                )
            except Exception as e:
                await db.rollback()
                raise e
        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
        return []


class ActionConsultarRankingSemanal(Action):
    def name(self) -> Text:
        return "action_consultar_ranking_semanal"

    async def run(self, dispatcher, tracker, domain):
        db = get_db_session()
        try:
            miembro = await get_miembro_from_tracker(tracker, db)
            if not miembro:
                dispatcher.utter_message(response="utter_error_accion")
                return []

            ranking = await obtener_ranking_hogar(db, miembro.id_hogar)

            if not ranking:
                dispatcher.utter_message(
                    text="¡El ranking de esta semana aún está vacío! ¡Es hora de completar algunas tareas!"
                )
            else:
                response_text = "¡Aquí está el podio de la semana para tu hogar! 🏆\n"
                iconos = ["🥇", "🥈", "🥉"]
                for i, entry in enumerate(ranking):
                    miembro_ranking = entry.get("miembro")
                    completadas = entry.get("tareas_completadas")
                    icono = iconos[i] if i < 3 else "🏅"
                    response_text += f"\n{icono} {miembro_ranking.nombre_completo} - {completadas} tarea(s)"
                dispatcher.utter_message(text=response_text)
        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
        return []


class ActionConsultarMiembrosHogar(Action):
    def name(self) -> Text:
        return "action_consultar_miembros_hogar"

    async def run(self, dispatcher, tracker, domain):
        db = get_db_session()
        try:
            miembro = await get_miembro_from_tracker(tracker, db)
            if not miembro:
                dispatcher.utter_message(response="utter_error_accion")
                return []

            miembros = await listar_miembros_activos_por_hogar(db, miembro.id_hogar)
            if not miembros:
                dispatcher.utter_message(
                    text=f"Parece que eres el único miembro registrado en el hogar {miembro.id_hogar} por ahora."
                )
            else:
                response_text = f"¡Claro! Los miembros activos en tu hogar (Hogar ID: {miembro.id_hogar}) son:\n"
                for i, m in enumerate(miembros):
                    response_text += f"\n- {m.nombre_completo} (Rol: {m.rol.nombre})"
                dispatcher.utter_message(text=response_text)
        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
        return []


# --- 4. ACCIONES DE ADMIN (¡NUEVAS!) ---


class ActionAdminListarTareasMiembro(Action):
    def name(self) -> Text:
        return "action_admin_listar_tareas_miembro"

    async def run(self, dispatcher, tracker, domain):
        db = get_db_session()
        try:
            admin = await get_miembro_from_tracker(tracker, db)
            if not admin or admin.rol.nombre != "Administrador":
                dispatcher.utter_message(response="utter_no_es_admin")
                return []

            miembro_nombre = next(
                tracker.get_latest_entity_values("miembro_nombre"), None
            )
            if not miembro_nombre:
                dispatcher.utter_message(
                    text="¿De qué miembro te gustaría ver las tareas?"
                )
                return []

            miembro_buscado = await obtener_miembro_por_nombre(
                db, miembro_nombre, admin.id_hogar
            )
            if not miembro_buscado:
                dispatcher.utter_message(
                    text=f"No encontré a un miembro llamado '{miembro_nombre}' en tu hogar."
                )
                return []

            tareas = await listar_tareas_por_miembro(db, miembro_buscado.id)
            if not tareas:
                dispatcher.utter_message(
                    text=f"¡Buenas noticias! Parece que {miembro_buscado.nombre_completo} no tiene tareas pendientes."
                )
            else:
                response_text = f"¡Claro! Aquí están las {len(tareas)} tareas pendientes de {miembro_buscado.nombre_completo}:\n"
                for i, tarea in enumerate(tareas):
                    response_text += f"\n- *{tarea.titulo}* (Estado: {tarea.estado_actual}, ID: {tarea.id})"
                dispatcher.utter_message(text=response_text)
        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
        return []


class ActionAdminListarTareasEstado(Action):
    def name(self) -> Text:
        return "action_admin_listar_tareas_estado"

    async def run(self, dispatcher, tracker, domain):
        db = get_db_session()
        try:
            admin = await get_miembro_from_tracker(tracker, db)
            if not admin or admin.rol.nombre != "Administrador":
                dispatcher.utter_message(response="utter_no_es_admin")
                return []

            estado = next(tracker.get_latest_entity_values("estado_tarea"), "pendiente")

            tareas = await listar_tareas_por_estado_y_hogar(db, estado, admin.id_hogar)

            if not tareas:
                dispatcher.utter_message(
                    text=f"No encontré tareas con el estado '{estado}' en tu hogar."
                )
            else:
                response_text = f"Encontré {len(tareas)} tareas en estado '{estado}':\n"
                for tarea in tareas:
                    nombre = (
                        tarea.miembro_asignado.nombre_completo
                        if hasattr(tarea, "miembro_asignado") and tarea.miembro_asignado
                        else "N/A"
                    )
                    response_text += (
                        f"\n- *{tarea.titulo}* (Asignada a: {nombre}, ID: {tarea.id})"
                    )
                dispatcher.utter_message(text=response_text)
        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
        return []


# --- 5. FORMULARIO DE CREAR TAREA (¡NUEVO!) ---


class ValidateCrearTareaForm(FormValidationAction):
    """Valida los slots del formulario 'crear_tarea_form'."""

    def name(self) -> Text:
        return "validate_crear_tarea_form"

    async def validate_slot_tarea_titulo(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if len(str(slot_value)) < 3:
            dispatcher.utter_message(
                text="El título parece muy corto. Intenta con uno más descriptivo (ej. 'Lavar los platos')."
            )
            return {"slot_tarea_titulo": None}
        return {"slot_tarea_titulo": slot_value}

    async def validate_slot_tarea_categoria(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # TODO: Cargar esto desde la API de Catálogos
        categorias_validas = [
            "limpieza",
            "cocina",
            "compras",
            "mantenimiento",
            "mascotas",
            "jardineria",
            "estudio",
            "recados",
            "organizacion",
            "basura",
        ]
        if str(slot_value).lower() not in categorias_validas:
            dispatcher.utter_message(
                text=f"No reconozco la categoría '{slot_value}'. Las válidas son: {', '.join(categorias_validas)}"
            )
            return {"slot_tarea_categoria": None}
        return {"slot_tarea_categoria": str(slot_value).lower()}

    async def validate_slot_tarea_asignado_a(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        db = get_db_session()
        try:
            admin = await get_miembro_from_tracker(tracker, db)
            if not admin:
                dispatcher.utter_message(response="utter_error_accion")
                return {"slot_tarea_asignado_a": None}

            miembro_asignado = await obtener_miembro_por_nombre(
                db, str(slot_value), admin.id_hogar
            )

            if not miembro_asignado:
                dispatcher.utter_message(
                    text=f"No encontré a un miembro llamado '{slot_value}' en tu hogar. ¿Quieres intentar con otro nombre?"
                )
                return {"slot_tarea_asignado_a": None}

            return {"slot_tarea_asignado_a": miembro_asignado.id}
        except Exception as e:
            print(f"[ERROR] validate_slot_tarea_asignado_a: {e}")
            dispatcher.utter_message(response="utter_error_bd")
            return {"slot_tarea_asignado_a": None}
        finally:
            await db.close()


class ActionCrearTarea(Action):
    """Acción final que guarda la tarea del formulario en la BD."""

    def name(self) -> Text:
        return "action_crear_tarea"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        db = get_db_session()
        try:
            admin = await get_miembro_from_tracker(tracker, db)
            if not admin or admin.rol.nombre != "Administrador":
                dispatcher.utter_message(response="utter_no_es_admin")
                return []

            titulo = tracker.get_slot("slot_tarea_titulo")
            categoria = tracker.get_slot("slot_tarea_categoria")
            asignado_a_id = tracker.get_slot("slot_tarea_asignado_a")

            if not all([titulo, categoria, asignado_a_id]):
                dispatcher.utter_message(
                    text="Faltaron datos para crear la tarea. Por favor, cancelando."
                )
                return [
                    SlotSet("slot_tarea_titulo", None),
                    SlotSet("slot_tarea_categoria", None),
                    SlotSet("slot_tarea_asignado_a", None),
                ]

            tarea_data = TareaCreate(
                titulo=titulo,
                categoria=categoria,
                asignado_a=asignado_a_id,
                id_hogar=admin.id_hogar,
            )

            try:
                tarea = await svc_crear_tarea(db, tarea_data, admin.id)
                await db.commit()
                dispatcher.utter_message(
                    text=f"¡Perfecto! He creado la tarea '{tarea.titulo}' (ID: {tarea.id}) y se la he asignado al miembro {asignado_a_id}."
                )
            except Exception as e:
                await db.rollback()
                raise e
        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()

        return [
            SlotSet("slot_tarea_titulo", None),
            SlotSet("slot_tarea_categoria", None),
            SlotSet("slot_tarea_asignado_a", None),
        ]


# --- 6. ACCIONES RESTANTES (A implementar) ---


class ActionExplicarTarea(Action):
    def name(self) -> Text:
        return "action_explicar_tarea"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(
            text="[ACCIÓN PENDIENTE] Aún no puedo explicar tareas."
        )
        return []


class ActionAgregarComentarioATarea(Action):
    def name(self) -> Text:
        return "action_agregar_comentario_tarea"

    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(
            text="[ACCIÓN PENDIENTE] Aún no puedo agregar comentarios."
        )
        return []


# ... (y así sucesivamente para todas las 40+ acciones) ...
