import requests
import json
import os
import time

RASA_URL = "http://localhost:5005"
SENDER = "tester"


def send_message(message: str):
    print(f"\n🧪 Enviando mensaje: {message}")

    response = requests.post(
        f"{RASA_URL}/webhooks/rest/webhook", json={"sender": SENDER, "message": message}
    )

    if response.status_code != 200:
        print("❌ Error comunicándose con Rasa:", response.text)
        return

    print("\n📩 Respuesta del bot:")
    for m in response.json():
        if "text" in m:
            print(" 👉", m["text"])
        if "image" in m:
            print(" 🖼 Imagen:", m["image"])

    # Pausa breve para que el tracker se actualice
    time.sleep(0.3)

    show_tracker_info()


def show_tracker_info():
    tracker = requests.get(f"{RASA_URL}/conversations/{SENDER}/tracker").json()

    print("\n🧠 === ESTADO DEL TRACKER ===")

    # Último intent
    try:
        intent = tracker["latest_message"]["intent"]["name"]
        confidence = tracker["latest_message"]["intent"]["confidence"]
        print(f"🎯 Intent detectado: {intent} (confianza: {confidence:.2f})")
    except:
        print("⚠ No se pudo leer el intent")

    # Slots
    print("\n📦 Slots actuales:")
    slots = tracker.get("slots", {})
    if slots:
        for k, v in slots.items():
            print(f" - {k}: {v}")
    else:
        print(" (No hay slots llenados aún)")

    # Acción previa
    try:
        latest_action = tracker["latest_action_name"]
        print(f"\n⚙ Última acción ejecutada: {latest_action}")
    except:
        print("\n⚠ No se pudo leer la acción previa")

    print("\n----------------------------------------\n")


def clear():
    os.system("cls" if os.name == "nt" else "clear")


# ------------------------------
#         MENU
# ------------------------------


def menu():
    while True:
        print(
            """
==============================================
   🧪 TEST INTERACTIVO AVANZADO DE RASA
==============================================

Seleccione una intención de prueba:

--- BÁSICAS ---
 1. Saludo
 2. Despedida
 3. Agradecimiento
 4. Ayuda

--- MIEMBROS (ADMIN) ---
 5. Crear miembro
 6. Actualizar miembro
 7. Eliminar miembro
 8. Listar miembros

--- COMENTARIOS ---
 9. Crear comentario
10. Actualizar comentario
11. Eliminar comentario

--- TAREAS ---
12. Consultar mis tareas
13. Ver comentarios de mi tarea
14. Agregar comentario a una tarea (admin)
15. Listar todas las tareas (admin)
16. Listar tareas por estado
17. Crear tarea simple (admin)
18. Crear tarea detallada (admin)
19. Actualizar tarea (admin)
20. Eliminar tarea (admin)
21. Listar tareas de un miembro (admin)

--- EVENTOS ---
22. Crear evento (admin)
23. Listar eventos (admin)

--- RANKING ---
24. Consultar mi ranking
25. Consultar ranking semanal

--- MIEMBROS ADMIN ---
26. Consultar miembros del hogar
27. Consultar miembro por nombre (admin)

--- SISTEMA ---
98. Ver tracker completo
99. Limpiar pantalla
0. Salir
"""
        )

        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            send_message("hola")
        elif opcion == "2":
            send_message("adios")
        elif opcion == "3":
            send_message("gracias")
        elif opcion == "4":
            send_message("ayuda")

        # ---------------------------
        # MIEMBROS
        # ---------------------------
        elif opcion == "5":
            send_message("quiero crear un miembro nuevo")
        elif opcion == "6":
            send_message("quiero actualizar un miembro")
        elif opcion == "7":
            send_message("quiero eliminar un miembro")
        elif opcion == "8":
            send_message("listar miembros registrados")

        # ---------------------------
        # COMENTARIOS
        # ---------------------------
        elif opcion == "9":
            send_message("quiero crear un comentario")
        elif opcion == "10":
            send_message("quiero actualizar un comentario")
        elif opcion == "11":
            send_message("quiero eliminar un comentario")

        # ---------------------------
        # TAREAS
        # ---------------------------
        elif opcion == "12":
            send_message("quiero ver mis tareas")
        elif opcion == "13":
            send_message("quiero ver comentarios de mi tarea")
        elif opcion == "14":
            send_message("agregar un comentario a una tarea")
        elif opcion == "15":
            send_message("listar todas las tareas")
        elif opcion == "16":
            send_message("listar tareas por estado")
        elif opcion == "17":
            send_message("crear tarea simple")
        elif opcion == "18":
            send_message("crear tarea detallada")
        elif opcion == "19":
            send_message("quiero actualizar una tarea")
        elif opcion == "20":
            send_message("quiero eliminar una tarea")
        elif opcion == "21":
            send_message("listar tareas de un miembro")

        # ---------------------------
        # EVENTOS
        # ---------------------------
        elif opcion == "22":
            send_message("crear evento")
        elif opcion == "23":
            send_message("listar eventos")

        # ---------------------------
        # RANKING
        # ---------------------------
        elif opcion == "24":
            send_message("consultar mi ranking")
        elif opcion == "25":
            send_message("consultar ranking semanal")

        # ---------------------------
        # MIEMBROS HOGAR
        # ---------------------------
        elif opcion == "26":
            send_message("consultar los miembros de mi hogar")
        elif opcion == "27":
            send_message("consultar miembro por nombre")

        # ---------------------------
        # UTILIDAD
        # ---------------------------
        elif opcion == "98":
            tracker = requests.get(f"{RASA_URL}/conversations/{SENDER}/tracker").json()
            print(json.dumps(tracker, indent=2, ensure_ascii=False))
        elif opcion == "99":
            clear()
        elif opcion == "0":
            print("👋 Saliendo...")
            break
        else:
            print("❌ Opción inválida")
        print("\n----------------------------------------------\n")


if __name__ == "__main__":
    clear()
    menu()
