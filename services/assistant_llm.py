"""
Cliente para consumir modelos OpenAI con soporte de tools/function-calling,
historial corto y contexto RAG. Usa ASCII para evitar problemas de encoding.
"""

import os
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from services.assistant_prompt import build_system_prompt

# Configuracion basica leida desde variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def get_client() -> AsyncOpenAI:
    """
    Crea el cliente asincrono de OpenAI leyendo las variables de entorno.
    Separado en funcion para facilitar mocking en pruebas.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("Falta OPENAI_API_KEY en el entorno.")

    return AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


def build_messages(
    mensaje_usuario: str,
    historial_corto: Optional[List[Dict[str, str]]] = None,
    respuesta_previa: Optional[str] = None,
    contexto_rag: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Construye la lista de mensajes para el LLM inyectando contexto:
    - historial_corto: ultimos turnos {"role": "user"|"assistant", "content": "..."}.
    - respuesta_previa: ultima respuesta del asistente para mantener coherencia.
    - contexto_rag: fragmentos recuperados (tareas/eventos/mensajes) para citar datos reales.
    - system_prompt: prompt base; si no se pasa, usa build_system_prompt().
    """
    system = system_prompt or build_system_prompt()
    messages: List[Dict[str, str]] = [{"role": "system", "content": system}]

    if contexto_rag:
        messages.append(
            {
                "role": "system",
                "content": f"Contexto recuperado (RAG):\n{contexto_rag}\nNo inventes datos fuera de este contexto.",
            }
        )

    if historial_corto:
        messages.extend(historial_corto)

    if respuesta_previa:
        messages.append(
            {
                "role": "system",
                "content": f"Ultima respuesta enviada al usuario (para coherencia): {respuesta_previa}",
            }
        )

    messages.append({"role": "user", "content": mensaje_usuario})
    return messages


async def completar_con_llm(
    mensaje_usuario: str,
    tools: Optional[List[Dict[str, Any]]] = None,
    system_prompt: Optional[str] = None,
    historial_corto: Optional[List[Dict[str, str]]] = None,
    respuesta_previa: Optional[str] = None,
    contexto_rag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Envia un mensaje al LLM con soporte de:
    - tools: definicion de funciones (OpenAI tools) para function-calling.
    - historial_corto/respuesta_previa: mantiene coherencia de conversacion.
    - contexto_rag: fragmentos relevantes recuperados.
    Devuelve el dict completo de la respuesta (model_dump()).
    """
    client = get_client()
    messages = build_messages(
        mensaje_usuario=mensaje_usuario,
        historial_corto=historial_corto,
        respuesta_previa=respuesta_previa,
        contexto_rag=contexto_rag,
        system_prompt=system_prompt,
    )

    completion = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        tools=tools or [],
        tool_choice="auto",
    )

    return completion.model_dump()
