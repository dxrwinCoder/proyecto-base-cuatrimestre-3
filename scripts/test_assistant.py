"""
Menu interactivo para probar el asistente (rol 2) contra /assistant/agent.
Permite lanzar consultas predefinidas que cubren las tools disponibles.
"""

import asyncio
import os
from typing import Dict, Any, List

import httpx

# Configuración por entorno para que no quede hardcodeado en el script
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ENDPOINT = f"{BASE_URL.rstrip('/')}/assistant/agent"
MIEMBRO_ID = int(os.getenv("ASISTENTE_MIEMBRO_ID", "2"))
ROL_ID = int(os.getenv("ASISTENTE_ROL_ID", "2"))

MENU_OPCIONES = {
    "1": ("Tareas pendientes", "¿Qué tareas tengo pendientes?"),
    "2": ("Tareas completadas", "Muéstrame mis tareas completadas del último mes"),
    "3": ("Eventos relacionados", "¿Qué eventos tengo esta semana?"),
    "4": ("Comentarios no leídos", "¿Tengo comentarios nuevos en mis tareas?"),
    "5": ("Mensajes no leídos", "¿Tengo mensajes sin leer?"),
    "6": ("Eventos hogar (mes)", "Muéstrame los eventos de este mes"),
    "7": ("Buscar tareas", "Busca tareas de mantenimiento"),
    "8": ("Crear tarea rápida", "Crea una tarea de limpieza para mañana"),
    "9": ("Resumen diario", "Dame un resumen diario"),
    "10": ("Ver calendario", "Muéstrame mi calendario"),
    "c": ("Consulta libre", None),
    "q": ("Salir", None),
}


async def llamar_agente(mensaje: str, historial: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    """Envía la consulta al endpoint /assistant/agent y devuelve el JSON."""
    payload = {
        "mensaje": mensaje,
        "miembro_id": MIEMBRO_ID,
        "rol_id": ROL_ID,
        "historial": historial or [],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(ENDPOINT, json=payload)
        resp.raise_for_status()
        return resp.json()


def imprimir_respuesta(data: Dict[str, Any]) -> None:
    """Imprime la respuesta del asistente de forma legible."""
    print("\n--- Respuesta ---")
    for bubble in data.get("bubbles", []):
        print(f"[{bubble.get('from')}] {bubble.get('text')}")
    if data.get("bullets"):
        print("- Bullets:")
        for b in data["bullets"]:
            print(f"  • {b}")
    if data.get("actions"):
        print("- Actions:")
        for a in data["actions"]:
            print(f"  • {a.get('label')} ({a.get('action')}) payload={a.get('payload')}")
    if data.get("intencion"):
        print(f"- Intención: {data.get('intencion')}")
    print("--- Fin respuesta ---\n")


async def menu():
    """Menu principal interactivo."""
    print(f"Usando endpoint: {ENDPOINT}")
    print(f"Miembro: {MIEMBRO_ID}, Rol: {ROL_ID}")
    while True:
        print("\n=== Menu Asistente ===")
        for k, v in MENU_OPCIONES.items():
            print(f"{k}) {v[0]}")
        opcion = input("Selecciona una opción: ").strip()
        if opcion.lower() == "q":
            break
        if opcion not in MENU_OPCIONES:
            print("Opción inválida.")
            continue

        titulo, mensaje_predef = MENU_OPCIONES[opcion]
        if opcion == "c":
            mensaje = input("Escribe tu consulta: ").strip()
        else:
            mensaje = mensaje_predef

        try:
            data = await llamar_agente(mensaje)
            print(f"\n[{titulo}]")
            imprimir_respuesta(data)
        except httpx.HTTPStatusError as exc:
            print(f"HTTP {exc.response.status_code}: {exc.response.text}")
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    asyncio.run(menu())
