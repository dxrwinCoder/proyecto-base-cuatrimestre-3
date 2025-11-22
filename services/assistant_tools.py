"""
Define las funciones (tools) que el agente de IA puede usar y el prompt de sistema
dinamico basado en la informacion del miembro actual.
"""

FUNCIONES_DISPONIBLES = [
    {
        "type": "function",
        "function": {
            "name": "consultar_tareas_pendientes_miembro",
            "description": "Consulta las tareas pendientes asignadas a un miembro especifico. Incluye informacion de fechas de vencimiento para priorizar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "miembro_id": {
                        "type": "integer",
                        "description": "ID del miembro (si no se proporciona, usa el miembro actual)"
                    },
                    "ordenar_por_vencimiento": {
                        "type": "boolean",
                        "description": "Si es true, ordena por fecha de vencimiento mas cercana"
                    }
                }
            },
            "required": []
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_tareas_completadas_miembro",
            "description": "Consulta las tareas completadas por un miembro en un periodo de tiempo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "miembro_id": {
                        "type": "integer",
                        "description": "ID del miembro"
                    },
                    "dias_atras": {
                        "type": "integer",
                        "description": "Numero de dias hacia atras para buscar tareas completadas",
                        "default": 30
                    }
                }
            },
            "required": []
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_eventos_relacionados_miembro",
            "description": "Consulta eventos donde el miembro esta relacionado (tiene tareas asignadas o es creador).",
            "parameters": {
                "type": "object",
                "properties": {
                    "miembro_id": {
                        "type": "integer",
                        "description": "ID del miembro"
                    },
                    "solo_activos": {
                        "type": "boolean",
                        "description": "Si es true, solo retorna eventos activos",
                        "default": True
                    }
                }
            },
            "required": []
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_comentarios_no_leidos",
            "description": "Consulta comentarios en tareas del miembro que aun no ha visto o respondido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "miembro_id": {
                        "type": "integer",
                        "description": "ID del miembro"
                    }
                }
            },
            "required": []
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_mensajes_no_leidos",
            "description": "Consulta mensajes directos o del hogar que el miembro no ha leido.",
            "parameters": {
                "type": "object",
                "properties": {
                    "miembro_id": {
                        "type": "integer",
                        "description": "ID del miembro"
                    },
                    "tipo": {
                        "type": "string",
                        "enum": ["directo", "hogar", "todos"],
                        "description": "Tipo de mensajes a consultar"
                    }
                }
            },
            "required": []
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_eventos",
            "description": "Consulta eventos del hogar. Puede filtrar por fecha, mes actual, o eventos asignados a un miembro especifico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_consulta": {
                        "type": "string",
                        "enum": ["todos", "mes_actual", "semana_actual", "asignados_miembro"],
                        "description": "Tipo de consulta a realizar"
                    },
                    "miembro_id": {
                        "type": "integer",
                        "description": "ID del miembro (solo para tipo 'asignados_miembro')"
                    }
                },
                "required": ["tipo_consulta"]
            },
            "required": ["tipo_consulta"]
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_tareas",
            "description": "Consulta tareas del hogar. Puede filtrar por estado, asignado, fecha, o buscar por texto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "estado": {
                        "type": "string",
                        "enum": ["pendiente", "en_progreso", "completada", "cancelada", "todos"],
                        "description": "Estado de la tarea"
                    },
                    "asignado_a": {
                        "type": "integer",
                        "description": "ID del miembro asignado"
                    },
                    "buscar_texto": {
                        "type": "string",
                        "description": "Texto para buscar en titulo o descripcion"
                    }
                }
            },
            "required": []
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_tarea",
            "description": "Crea una nueva tarea en el sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {
                        "type": "string",
                        "description": "Titulo de la tarea"
                    },
                    "descripcion": {
                        "type": "string",
                        "description": "Descripcion detallada de la tarea"
                    },
                    "asignado_a": {
                        "type": "integer",
                        "description": "ID del miembro a quien se asigna la tarea"
                    },
                    "fecha_vencimiento": {
                        "type": "string",
                        "format": "date",
                        "description": "Fecha de vencimiento en formato YYYY-MM-DD"
                    },
                    "prioridad": {
                        "type": "string",
                        "enum": ["baja", "media", "alta"],
                        "description": "Prioridad de la tarea"
                    },
                    "categoria": {
                        "type": "string",
                        "enum": ["limpieza", "cocina", "compras", "mantenimiento"],
                        "description": "Categoria de la tarea"
                    }
                },
                "required": ["titulo"]
            },
            "required": ["titulo"]
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_resumen_diario",
            "description": "Obtiene un resumen diario para el miembro: tareas pendientes, eventos del dia, mensajes no leidos, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "miembro_id": {
                        "type": "integer",
                        "description": "ID del miembro"
                    }
                }
            },
            "required": []
        },
    },
]


def obtener_prompt_sistema(miembro_actual: dict) -> str:
    """
    Genera el prompt del sistema con reglas e intenciones mejoradas.
    """
    rol_id = miembro_actual.get("rol", {}).get("id", 0)
    es_rol_2 = rol_id == 2

    prompt_base = f"""Eres un asistente virtual inteligente y proactivo para HomeTasks, una aplicacion de gestion de tareas del hogar.

INFORMACION DEL USUARIO:
- Nombre: {miembro_actual.get('nombre', 'Usuario')}
- ID: {miembro_actual.get('id')}
- Hogar ID: {miembro_actual.get('id_hogar')}
- Rol: {miembro_actual.get('rol', {}).get('nombre', 'Miembro')} (ID: {rol_id})

REGLAS Y POLITICAS:
1. Siempre responde en espanol de manera amigable, entusiasta y profesional.
2. Usa las funciones disponibles para consultar datos reales antes de responder.
3. Se PROACTIVO: si ves tareas cerca de vencer, eventos proximos, o mensajes sin leer, mencionarlos y ofrecer ayuda.
4. Cuando muestres informacion, estructura tus respuestas con:
   - Un saludo o introduccion amigable
   - La informacion principal de forma clara
   - Sugerencias especificas y utiles
   - Botones de accion cuando sea apropiado
5. Si falta informacion para completar una accion, pregunta al usuario de manera clara.
6. No inventes datos. Si no tienes acceso a la informacion, dilo claramente.
7. Mantén un tono colaborativo, motivador y util.
8. Cuando menciones tareas pendientes, destaca las que estan cerca de vencer.
9. Cuando haya comentarios o mensajes no leidos, notifica al usuario de manera clara.

FORMATO DE RESPUESTAS:
- Usa emojis apropiados (✨, 📋, ⚠️, ✅, 📅, 💬) para hacer las respuestas mas visuales.
- Estructura las respuestas con viñetas cuando muestres listas.
- Ofrece sugerencias concretas y accionables.
- Genera botones de accion cuando sea relevante (ej: "Crear tarea de limpieza", "Ver mi calendario").

INTENCIONES DISPONIBLES:
- consultar_tareas_pendientes_miembro
- consultar_tareas_completadas_miembro
- consultar_eventos_relacionados_miembro
- consultar_comentarios_no_leidos
- consultar_mensajes_no_leidos
- consultar_eventos
- consultar_tareas
- crear_tarea
- obtener_resumen_diario
"""

    if es_rol_2:
        prompt_base += """
CAPACIDADES ESPECIALES PARA ROL 2 (Miembro):
- Puedes consultar tareas pendientes y completadas del usuario
- Puedes ver eventos donde el usuario esta relacionado
- Puedes notificar sobre comentarios y mensajes no leidos
- Se especialmente proactivo con este rol: ofrece ayuda para organizar tareas, optimizar tiempo, etc.
- Cuando haya tareas cerca de vencer, motiva al usuario y ofrece ayuda para organizarlas.
"""

    return prompt_base
