# probar_rasa_interactivo.py
import httpx
import asyncio
import sys
from rich import print

# --- 1. CONFIGURACIÓN DEL SCRIPT ---
# Asegúrese de que estas URLs coincidan con sus servidores en ejecución
FASTAPI_URL = "http://localhost:8000"
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

# Credenciales de los usuarios de prueba (deben existir en su BD)
ADMIN_CREDS = {"correo_electronico": "admin@example.com", "contrasena": "admin12345"}
USER_CREDS = {"correo_electronico": "emanuel@ejemplo.com", "contrasena": "emanuel12345"}

# --- 2. FUNCIONES DE CLIENTE ---

def get_jwt_token(email, password):
    """
    Se autentica contra la API de FastAPI para obtener un token real.
    """
    print(f"\n[INFO] Autenticando a [bold]{email}[/bold] contra FastAPI ({FASTAPI_URL})...")
    try:
        r = httpx.post(
            f"{FASTAPI_URL}/auth/login", 
            json={"correo_electronico": email, "contrasena": password}
        )
        r.raise_for_status()
        token = r.json().get("access_token")
        
        if not token:
            print(f"[ERROR] La respuesta de Login no contenía 'access_token'.")
            return None
            
        print(f"[SUCCESS] Token JWT obtenido para [bold]{email}[/bold].")
        return token
    except httpx.RequestError as e:
        print(f"[ERROR_FATAL] No se pudo conectar a la API de FastAPI en {FASTAPI_URL}.")
        print(f"       Detalle: {e}")
        print("       (¿Está ejecutando 'uvicorn main:app'?)")
        return None
    except httpx.HTTPStatusError as e:
        print(f"[ERROR_FATAL] Falló el login en FastAPI (Status: {e.response.status_code}).")
        print(f"       Respuesta: {e.response.text}")
        return None

async def send_rasa_message(sender_id: str, message: str, token: str):
    """
    Envía un mensaje al servidor Rasa, incluyendo el token JWT
    en el 'metadata' para que el Action Server lo use.
    """
    payload = {
        "sender": sender_id,
        "message": message,
        "metadata": {
            "token": token  # <-- ¡La clave de la integración!
        }
    }
    
    print(f"\n[bold]>{'='*10} Enviando a Rasa ({sender_id}) {'='*10}>[/bold]")
    print(f"[USER] {message}")
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(RASA_URL, json=payload, timeout=20)
            r.raise_for_status()
            
            responses = r.json()
            print("[BOT] Respuestas recibidas:")
            if not responses:
                print("   [italic](El bot no generó una respuesta visible)[/italic]")
                
            for resp in responses:
                print(f"   -> [green]{resp.get('text')}[/green]")
            return responses
            
        except httpx.RequestError as e:
            print(f"[ERROR_FATAL] No se pudo conectar al servidor Rasa en {RASA_URL}.")
            print(f"       Detalle: {e}")
            print("       (¿Está ejecutando 'rasa run --enable-api'?)")
        except httpx.HTTPStatusError as e:
            print(f"[ERROR_FATAL] El servidor Rasa devolvió un error (Status: {e.response.status_code}).")
            print(f"       Respuesta: {e.response.text}")

# --- 3. LÓGICA DEL MENÚ INTERACTIVO ---

# Mapeo de intenciones para selección manual
INTENT_MENU = {
    "1": ("saludar", "Hola"),
    "2": ("consultar_mis_tareas", "¿Cuáles son mis tareas?"),
    "3": ("consultar_ranking_semanal", "¿Cómo va el ranking de la semana?"),
    "4": ("marcar_tarea_completada", "Marca la tarea {nombre} como completada"),
    "5": ("agregar_comentario_tarea", "Agrega un comentario a la tarea {id}: {contenido}"),
    "6": ("consultar_miembros_hogar", "¿Quiénes viven en mi hogar?"),
    "7.": ("sugerir_tarea_miembro", "Sugiéreme una tarea para {nombre}"),
    "8": ("nlu_fallback", "cuánto es dos más dos"),
    "9": ("despedirse", "Adiós")
}

def print_menu():
    """Imprime el menú de intenciones."""
    print("\n--- [bold blue]Menú de Intenciones[/bold blue] ---")
    for key, (intent, text) in INTENT_MENU.items():
        print(f"  {key}. [cyan]{intent}[/cyan] (Ej: '{text}')")
    print("  0. Salir")

async def main_interactive_test():
    """Bucle principal del script de prueba."""
    
    # 1. Obtener tokens de ambos usuarios
    admin_token = get_jwt_token(ADMIN_CREDS["correo_electronico"], ADMIN_CREDS["contrasena"])
    user_token = get_jwt_token(USER_CREDS["correo_electronico"], USER_CREDS["contrasena"])
    
    if not admin_token or not user_token:
        print("\n[ERROR_FATAL] Faltan tokens para continuar. Saliendo.")
        return

    current_token = None
    current_sender_id = None

    while True:
        # 2. Seleccionar el "perfil" (token)
        print("\n--- [bold blue]Selección de Perfil[/bold blue] ---")
        print("1. Probar como Administrador (admin@example.com)")
        print("2. Probar como Usuario (hijo@example.com)")
        print("0. Salir")
        profile_choice = input("Seleccione un perfil para probar: ")
        
        if profile_choice == "1":
            current_token = admin_token
            current_sender_id = "admin_tester"
        elif profile_choice == "2":
            current_token = user_token
            current_sender_id = "user_tester"
        elif profile_choice == "0":
            break
        else:
            print("[yellow]Opción no válida.[/yellow]")
            continue
            
        print(f"[INFO] Perfil [bold]{current_sender_id}[/bold] seleccionado.")

        # 3. Bucle de prueba de intenciones
        while True:
            print_menu()
            intent_choice = input(f"Seleccione intención para '{current_sender_id}' (o 'm' para cambiar de perfil): ")
            
            if intent_choice == "0" or intent_choice.lower() == "exit":
                print("[INFO] Saliendo del script de prueba...")
                return
            if intent_choice.lower() == "m" or intent_choice.lower() == "menu":
                print("[INFO] Regresando al menú de perfil...")
                break
                
            if intent_choice not in INTENT_MENU:
                print("[yellow]Opción de intención no válida.[/yellow]")
                continue
                
            intent_key, message_template = INTENT_MENU[intent_choice]
            message_to_send = message_template

            # 4. Manejo de Entidades (Slots)
            # (Este es el reemplazo manual de entidades)
            if "{nombre}" in message_template:
                nombre = input("   -> Ingrese entidad [nombre]: ")
                message_to_send = message_to_send.replace("{nombre}", nombre)
            if "{id}" in message_template:
                id_tarea = input("   -> Ingrese entidad [id] de tarea: ")
                message_to_send = message_to_send.replace("{id}", id_tarea)
            if "{contenido}" in message_template:
                contenido = input("   -> Ingrese entidad [contenido]: ")
                message_to_send = message_to_send.replace("{contenido}", contenido)
            
            # 5. Enviar mensaje a Rasa
            await send_rasa_message(current_sender_id, message_to_send, current_token)

if __name__ == "__main__":
    print("[INFO] Iniciando Script de Pruebas Interactivas E2E para Rasa...")
    asyncio.run(main_interactive_test())