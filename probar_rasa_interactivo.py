from fastapi import FastAPI
import requests
from typing import Optional
import logging

# Config
API_BASE = "http://localhost:8000"  # FastAPI
RASA_ENDPOINT = "http://localhost:5005/webhooks/rest/webhook"

# Credenciales para obtener tokens reales
ADMIN_LOGIN = {
    "correo_electronico": "adminmaestro@example.com",
    "contrasena": "admin123",
}
MIEMBRO_LOGIN = {
    "correo_electronico": "miembro@example.com",
    "contrasena": "miembro123",
}

# Se llena tras login
ADMIN_META: dict = {}
MIEMBRO_META: dict = {}

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("rasa_tester")

app = FastAPI(
    title="Tester del Chatbot Rasa",
    description="API y CLI para probar intenciones de Rasa",
    version="1.1.2",
)


# ------------------ Utilidades ------------------
def _login_y_meta(login_payload: dict) -> Optional[dict]:
    """Hace login en la API para obtener token e IDs"""
    try:
        log.info(f"Autenticando contra API {API_BASE}/auth/login")
        resp = requests.post(f"{API_BASE}/auth/login", json=login_payload, timeout=10)
        if resp.status_code != 200:
            log.error(f"Login falló {resp.status_code}: {resp.text}")
            return None
        data = resp.json()
        token = data.get("access_token")
        miembro_id = data.get("id_miembro") or data.get("id") or data.get("sub")
        id_hogar = data.get("id_hogar")
        id_rol = data.get("id_rol")
        if not token or not miembro_id:
            log.error("Login sin token o id_miembro en respuesta")
            return None

        # Si falta id_rol o id_hogar, consultar perfil
        if id_rol is None or id_hogar is None:
            try:
                pf = requests.get(
                    f"{API_BASE}/miembros/perfil",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if pf.status_code == 200:
                    pdata = pf.json()
                    id_hogar = id_hogar or pdata.get("id_hogar")
                    id_rol = id_rol or pdata.get("id_rol")
                    log.info("Perfil consultado para completar id_hogar/id_rol")
                else:
                    log.warning(
                        f"No se pudo leer perfil (status {pf.status_code}): {pf.text}"
                    )
            except Exception as e:
                log.warning(f"No se pudo completar datos desde perfil: {e}")

        return {
            "token": token,
            "id_miembro": miembro_id,
            "id_hogar": id_hogar,
            "id_rol": id_rol,
        }
    except Exception as e:
        log.exception(f"Error en login: {e}")
        return None


# ------------------ Rasa ------------------
def send_to_rasa(
    message: str, sender: str = "tester_user", metadata: Optional[dict] = None
):
    payload = {"sender": sender, "message": message}
    if metadata:
        payload["metadata"] = metadata
    log.info(f"→ Rasa msg: {payload}")
    response = requests.post(RASA_ENDPOINT, json=payload)
    try:
        data = response.json()
        log.info(f"← Rasa resp: {data}")
        return data
    except Exception:
        log.error("No se pudo interpretar la respuesta de Rasa.")
        return {"error": "No se pudo interpretar la respuesta de Rasa."}


def _formatear_respuesta(resp):
    """Devuelve estructura amigable para consola/cliente."""
    if resp is None:
        return {"status": "error", "texto": "Sin respuesta"}
    if isinstance(resp, dict) and "error" in resp:
        return {"status": "error", "texto": resp.get("error"), "raw": resp}
    textos = []
    if isinstance(resp, list):
        for item in resp:
            if isinstance(item, dict):
                if "text" in item:
                    textos.append(item["text"])
                elif "custom" in item:
                    textos.append(str(item["custom"]))
    elif isinstance(resp, dict) and "text" in resp:
        textos.append(resp["text"])
    texto_final = " | ".join(textos) if textos else str(resp)
    return {"status": "ok", "texto": texto_final, "raw": resp}


# ------------------ API FastAPI ------------------
@app.post("/send/")
def send_message(text: str):
    return send_to_rasa(text)


@app.get("/menu")
def menu():
    opciones = {
        "1": "Listar tareas hogar (admin)",
        "2": "Crear tarea para miembro (admin)",
        "3": "Crear evento (admin)",
        "4": "Listar eventos hogar (admin)",
        "5": "Listar notificaciones (admin)",
        "10": "Consultar mis tareas (miembro)",
        "11": "Consultar eventos hogar (miembro)",
        "15": "Mis eventos mes actual (miembro)",
        "16": "Mis eventos semana actual (miembro)",
        "17": "Mis notificaciones (miembro)",
        "18": "Detalle tiempos de mis tareas (miembro)",
        "12": "Saludo (miembro)",
        "13": "Despedida (miembro)",
        "14": "Agradecimiento (miembro)",
    }
    return opciones


@app.get("/run-test/{opcion}")
def run_test(opcion: int):
    pruebas = {
        1: {"msgs": ["muestra todas las tareas del hogar"], "meta": ADMIN_META},
        2: {
            "msgs": [
                "crea una tarea para el usuario 2",
                "el título es Lavar platos",
                "descríbela como limpiar cocina",
            ],
            "meta": ADMIN_META,
        },
        3: {
            "msgs": [
                "crea un evento",
                "título Reunion semanal",
                "fecha 2025-12-31T18:00:00",
                "descripcion cerramos tareas",
            ],
            "meta": ADMIN_META,
        },
        4: {"msgs": ["muestra los eventos del hogar"], "meta": ADMIN_META},
        5: {"msgs": ["listar notificaciones del hogar"], "meta": ADMIN_META},
        10: {"msgs": ["qué tareas tengo"], "meta": MIEMBRO_META},
        11: {"msgs": ["qué eventos hay en mi hogar"], "meta": MIEMBRO_META},
        15: {"msgs": ["eventos que tengo este mes"], "meta": MIEMBRO_META},
        16: {"msgs": ["eventos de esta semana en los que participo"], "meta": MIEMBRO_META},
        17: {"msgs": ["muéstrame mis notificaciones"], "meta": MIEMBRO_META},
        18: {"msgs": ["detalle de tiempo de mis tareas"], "meta": MIEMBRO_META},
        12: {"msgs": ["hola"], "meta": MIEMBRO_META},
        13: {"msgs": ["adiós"], "meta": MIEMBRO_META},
        14: {"msgs": ["gracias"], "meta": MIEMBRO_META},
    }

    if opcion not in pruebas:
        return {"error": "Opción no válida, revisa /menu"}

    mensajes = pruebas[opcion]["msgs"]
    meta = pruebas[opcion]["meta"]

    respuestas = []
    for msg in mensajes:
        r = send_to_rasa(msg, metadata=meta)
        respuestas.append({"enviado": msg, "respuesta": _formatear_respuesta(r)})

    return respuestas


# ------------------ CLI interactivo ------------------
def menu_interactivo():
    # Login automático para rellenar los meta
    global ADMIN_META, MIEMBRO_META
    ADMIN_META = _login_y_meta(ADMIN_LOGIN) or ADMIN_META
    MIEMBRO_META = _login_y_meta(MIEMBRO_LOGIN) or MIEMBRO_META

    roles = {"admin": ADMIN_META, "miembro": MIEMBRO_META}
    print("Selecciona rol (admin/miembro). Otro valor = admin por defecto.")
    rol = input("Rol: ").strip().lower() or "admin"
    meta_sel = roles.get(rol, ADMIN_META)
    log.info(f"Usando rol '{rol}' con meta: {meta_sel}")

    print(
        """
============================
 TESTER DEL CHATBOT RASA
============================
Rol Admin:
 1. Listar tareas hogar
 2. Crear tarea para miembro
 3. Crear evento
 4. Listar eventos hogar
 5. Listar notificaciones

Rol Miembro:
 10. Consultar mis tareas
 11. Consultar eventos hogar
 12. Saludo
 13. Despedida
 14. Agradecimiento
 15. Mis eventos mes actual
 16. Mis eventos semana actual
 17. Mis notificaciones
 18. Detalle tiempos de mis tareas

0. Salir
"""
    )

    while True:
        try:
            opcion = int(input("Selecciona una opción: "))
        except Exception:
            print("Debe ser un número.")
            continue

        if opcion == 0:
            print("Saliendo...")
            break

        print("Ejecutando pruebas...")
        try:
            # Inyecta el meta seleccionado antes de ejecutar
            if opcion in (1, 2, 3, 4, 5):
                ADMIN_META.update(meta_sel or {})
            else:
                MIEMBRO_META.update(meta_sel or {})
            resultado = run_test(opcion)  # Llama directo, sin HTTP local
        except Exception as e:
            log.exception("Error ejecutando prueba")
            resultado = {"error": str(e)}
        print(resultado)
        print("\n----------------------------\n")


if __name__ == "__main__":
    import sys

    # Ejecutar menú interactivo directo: python probar_rasa_interactivo.py menu
    if len(sys.argv) > 1 and sys.argv[1].lower() == "menu":
        menu_interactivo()
    else:
        import uvicorn

        # Ejecutar el tester como mini API en puerto 8010
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8010,
            reload=True,
        )
