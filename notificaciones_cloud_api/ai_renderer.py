import json
from typing import List

from services.assistant_llm import completar_con_llm, OPENAI_MODEL
from utils.logger import setup_logger

logger = setup_logger("whatsapp_ai_renderer")


async def render_body_vars_with_ai(
    contexto: dict,
    variable_order: List[str],
    plantilla: str,
    fallback: List[str],
) -> List[str]:
    """
    Usa el LLM ya configurado en el proyecto para generar las variables de cuerpo
    respetando el orden y la cantidad de la plantilla aprobada por Meta.
    """
    prompt = (
        "Eres un asistente que arma variables para una plantilla aprobada de WhatsApp. "
        "Debes regresar un JSON con la clave 'variables' como lista de strings en el mismo orden proporcionado. "
        "No cambies la cantidad de variables ni agregues texto fuera del JSON. "
        f"Plantilla: {plantilla}. "
        f"Orden de variables: {variable_order}. "
        "Traduce el contexto a mensajes claros y cortos para cada variable (maximo 80 caracteres por variable). "
        "Si falta informacion deja una frase breve como 'Sin dato'."
    )

    user_message = (
        "Genera la lista 'variables' para la plantilla. "
        f"Contexto JSON: {json.dumps(contexto, default=str)}"
    )

    try:
        completion = await completar_con_llm(
            mensaje_usuario=user_message,
            system_prompt=prompt,
            tools=None,
            historial_corto=None,
            respuesta_previa=None,
            contexto_rag=None,
        )
        logger.debug("Respuesta cruda del LLM recibida")
        message = completion["choices"][0]["message"]["content"]
        data = json.loads(message)
        variables = data.get("variables")
        if (
            isinstance(variables, list)
            and len(variables) == len(variable_order)
            and all(isinstance(v, str) for v in variables)
        ):
            return variables
            logger.warning(
                "Respuesta del LLM no valida, se usa fallback. Contenido: %s", message
            )
            return fallback
    except Exception as exc:  # pragma: no cover - defensa en runtime
        logger.error("No se pudieron generar variables con IA: %s", exc)
        return fallback
