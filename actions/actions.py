import jwt
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# --- 1. IMPORTACIONES DE SU PROYECTO FASTAPI ---
# (Esto asume que 'rasa run actions' se ejecuta desde la carpeta raíz 'app/')
try:
    # Importar el generador de sesión y el modelo base
    from db.database import AsyncSessionLocal
    from models.miembro import Miembro
    from models.tarea import Tarea
    
    # Importar los schemas necesarios
    from schemas.tarea import TareaCreate
    from schemas.comentario_tarea import ComentarioTareaCreate
    
    # Importar los servicios "calibrados"
    from services.tarea_service import (
        crear_tarea,
        obtener_tarea_por_id,
        listar_tareas_por_miembro,
        actualizar_estado_tarea,
        agregar_comentario_a_tarea,
        listar_tareas_por_evento,
        listar_tareas_por_tipo
    )
    # (Importar los servicios faltantes cuando estén listos)
    # from services.ranking_service import obtener_ranking_hogar
    # from services.notificacion_service import listar_notificaciones_por_miembro
    # from services.miembro_service import obtener_miembro_por_nombre

except ImportError as e:
    print("\n[ERROR DE ACCIÓN RASA] No se pudieron importar los módulos de FastAPI.")
    print(f"Detalle: {e}")
    print("Asegúrese de ejecutar 'rasa run actions' desde la carpeta raíz 'app/' de su proyecto.")
    exit(1)

# --- 2. CONFIGURACIÓN DE JWT Y SESIÓN DE BD ---

# (Valores que usted proporcionó)
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

def get_db_session() -> AsyncSession:
    """Crea y devuelve una nueva sesión asíncrona de SQLAlchemy."""
    return AsyncSessionLocal()


async def get_miembro_from_tracker(tracker: Tracker, db: AsyncSession) -> Miembro | None:
    """
    Decodifica el token JWT enviado en el 'metadata' y obtiene el Miembro.
    """
    metadata = tracker.get_slot("session_started_metadata") or {}
    token = metadata.get("token")

    if not token:
        print("[ERROR DE ACCIÓN RASA] No se recibió token en 'metadata'.")
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        miembro_id = payload.get("sub")
        
        if not miembro_id:
            print("[ERROR DE ACCIÓN RASA] Token inválido (no 'sub').")
            return None
        
        # Obtener el miembro completo desde la BD
        miembro = await db.get(Miembro, int(miembro_id))
        if not miembro:
            print(f"[ERROR DE ACCIÓN RASA] Miembro ID {miembro_id} no encontrado en la BD.")
            return None
            
        print(f"[INFO DE ACCIÓN RASA] Miembro autenticado: {miembro.correo_electronico} (ID: {miembro.id})")
        return miembro
        
    except jwt.PyJWTError as e:
        print(f"[ERROR DE ACCIÓN RASA] Error de JWT: {e}")
        return None
    except Exception as e:
        print(f"[ERROR DE ACCIÓN RASA] Error de BD al obtener miembro: {e}")
        return None

# --- 3. ACCIONES DE TAREAS (IMPLEMENTADAS) ---

class ActionConsultarMisTareas(Action):
    """Acción para la intención 'consultar_mis_tareas'."""

    def name(self) -> Text:
        return "action_consultar_mis_tareas"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        db = get_db_session()
        try:
            miembro = await get_miembro_from_tracker(tracker, db)
            if not miembro:
                dispatcher.utter_message(text="Error de autenticación. No pude verificar quién eres.")
                return []

            # Llamar al servicio de producción
            tareas = await listar_tareas_por_miembro(db, miembro.id)
            
            if not tareas:
                dispatcher.utter_message(text=f"¡Buenas noticias, {miembro.nombre_completo}! No tienes tareas pendientes.")
            else:
                response_text = f"Hola {miembro.nombre_completo}, tienes {len(tareas)} tarea(s) pendiente(s):\n"
                for i, tarea in enumerate(tareas):
                    response_text += f"\n{i+1}. {tarea.titulo} (ID: {tarea.id})"
                dispatcher.utter_message(text=response_text)
                
        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
                
        return []

class ActionExplicarTarea(Action):
    """Acción para 'preguntar_como_hacer_tarea'"""
    def name(self) -> Text:
        return "action_explicar_tarea"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        db = get_db_session()
        try:
            miembro = await get_miembro_from_tracker(tracker, db)
            if not miembro:
                dispatcher.utter_message(text="Error de autenticación.")
                return []
            
            tarea_id = next(tracker.get_latest_entity_values("tarea_id"), None)
            
            if not tarea_id:
                dispatcher.utter_message(text="¿De qué ID de tarea quieres saber la descripción?")
                return []

            tarea = await obtener_tarea_por_id(db, int(tarea_id))
            
            if not tarea or tarea.id_hogar != miembro.id_hogar:
                dispatcher.utter_message(text=f"Lo siento, no encontré la tarea con ID {tarea_id} en tu hogar.")
                return []
            
            response = f"Claro. La descripción de la tarea '{tarea.titulo}' (ID: {tarea.id}) es: \n\n{tarea.descripcion or 'No se proporcionó una descripción.'}"
            dispatcher.utter_message(text=response)

        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
        return []

class ActionMarcarTareaCompletada(Action):
    """Acción para 'marcar_tarea_completada'"""
    def name(self) -> Text:
        return "action_marcar_tarea_completada"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        db = get_db_session()
        try:
            miembro = await get_miembro_from_tracker(tracker, db)
            if not miembro:
                dispatcher.utter_message(text="Error de autenticación.")
                return []

            tarea_nombre = next(tracker.get_latest_entity_values("tarea_nombre"), None)
            tarea_id_str = next(tracker.get_latest_entity_values("tarea_id"), None)
            
            if not tarea_nombre and not tarea_id_str:
                dispatcher.utter_message(text="¿Qué tarea deseas marcar como completada? Puedes decirme su nombre o ID.")
                return []

            tarea_a_actualizar = None
            if tarea_id_str:
                tarea_a_actualizar = await obtener_tarea_por_id(db, int(tarea_id_str))
            else:
                # Lógica de búsqueda por nombre (simplificada)
                stmt = select(Tarea).where(
                    Tarea.titulo.like(f"%{tarea_nombre}%"), 
                    Tarea.asignado_a == miembro.id,
                    Tarea.estado_actual != "completada"
                )
                tarea_a_actualizar = (await db.execute(stmt)).scalar_one_or_none()

            if not tarea_a_actualizar:
                dispatcher.utter_message(text=f"No encontré una tarea pendiente llamada '{tarea_nombre or tarea_id_str}' asignada a ti.")
                return []
                
            # Llamar al servicio (replicando la lógica de la ruta)
            try:
                await actualizar_estado_tarea(db, tarea_a_actualizar.id, "completada", miembro.id)
                await db.commit() # ¡La acción es dueña de la transacción!
                dispatcher.utter_message(text=f"¡Excelente! He marcado la tarea '{tarea_a_actualizar.titulo}' (ID: {tarea_a_actualizar.id}) como completada.")
            except Exception as e:
                await db.rollback()
                raise e

        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
                
        return []

class ActionAgregarComentarioATarea(Action):
    """Acción para 'agregar_comentario_tarea'"""
    def name(self) -> Text:
        return "action_agregar_comentario_tarea"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        db = get_db_session()
        try:
            miembro = await get_miembro_from_tracker(tracker, db)
            if not miembro:
                dispatcher.utter_message(text="Error de autenticación.")
                return []

            # Obtener entidades
            contenido = next(tracker.get_latest_entity_values("contenido_comentario"), None)
            tarea_id_str = next(tracker.get_latest_entity_values("tarea_id"), None)
            
            if not contenido or not tarea_id_str:
                dispatcher.utter_message(text="Necesito saber el ID de la tarea y el contenido del comentario, por favor.")
                return []

            # Verificar que la tarea existe y pertenece al hogar
            tarea = await obtener_tarea_por_id(db, int(tarea_id_str))
            if not tarea or tarea.id_hogar != miembro.id_hogar:
                dispatcher.utter_message(text=f"No encontré la tarea con ID {tarea_id_str} en tu hogar.")
                return []
                
            # Llamar al servicio (replicando la lógica de la ruta)
            try:
                schema_data = ComentarioTareaCreate(
                    id_tarea=tarea.id,
                    contenido=contenido
                )
                await agregar_comentario_a_tarea(db, schema_data, miembro.id)
                await db.commit() # ¡La acción es dueExiña de la transacción!
                dispatcher.utter_message(text=f"¡Listo! He agregado tu comentario a la tarea '{tarea.titulo}'.")
            except Exception as e:
                await db.rollback()
                raise e

        except Exception as e:
            print(f"[ERROR] {self.name()}: {e}")
            dispatcher.utter_message(response="utter_error_bd")
        finally:
            await db.close()
                
        return []

# --- 4. ACCIONES PENDIENTES (FALTAN SERVICIOS) ---

# class ActionConsultarRankingSemanal(Action):
#     def name(self) -> Text:
#         return "action_consultar_ranking_semanal"
#     async def run(self, dispatcher, tracker, domain):
#         dispatcher.utter_message(text="[ACCIÓN PENDIENTE] Aún no puedo consultar el ranking.")
#         return []

# class ActionSugerirTareaMiembro(Action):
#     def name(self) -> Text:
#         return "action_sugerir_tarea_miembro"
#     async def run(self, dispatcher, tracker, domain):
#         dispatcher.utter_message(text="[ACCIÓN PENDIENTE] Aún no puedo sugerir tareas.")
#         return []

# (Y así sucesivamente para las 30+ acciones restantes...)