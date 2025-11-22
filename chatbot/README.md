# Chatbot transaccional con Rasa + spaCy

Este ejemplo prepara un agente transaccional para HomeTasks usando Rasa 3.6, spaCy y un servidor de acciones que conversa con FastAPI/MySQL. Se asume **Python 3.10** y **Pydantic v1** dentro de un entorno virtual.

## Estructura rápida

```
chatbot/
├── actions/             # Servidor de acciones (puerto 5055)
├── data/                # NLU, reglas e historias
├── config.yml           # Pipeline spaCy en español
├── credentials.yml      # Habilita el canal REST
├── domain.yml           # Intents, slots, formularios y respuestas
├── endpoints.yml        # Endpoint del servidor de acciones
├── requirements.txt     # Dependencias (pydantic<2)
└── README.md            # Esta guía
```

## Configuración del entorno (Python 3.10)

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download es_core_news_md
```

> Nota: Rasa 3.6 y rasa-sdk 3.6 ya dependen de Pydantic v1, y `pydantic<2` se fija explícitamente para evitar conflictos.

## Entrenamiento y ejecución

1. **Entrenar NLU/Diálogo**

   ```bash
   rasa train --config config.yml --domain domain.yml --data data
   ```

2. **Levantar el servidor de acciones (puerto 5055)**

   ```bash
   rasa run actions --actions chatbot.actions.actions --port 5055
   ```

3. **Levantar el servidor Rasa (puerto 5005)**

   ```bash
   rasa run --enable-api --port 5005 --endpoints endpoints.yml --credentials credentials.yml
   ```

## Flujo de Triángulo de Comunicación

1. El **cliente** obtiene primero su JWT desde FastAPI (`POST /auth/login`).
2. Envía el mensaje a Rasa (puerto 5005) **incluyendo el token en `metadata.jwt_token`**.
3. Rasa clasifica la intención, ejecuta acciones personalizadas y delega la llamada al servidor de acciones (puerto 5055).
4. Las **acciones** decodifican/reenvían el JWT a FastAPI (puerto 8000), consumen servicios reales y formatean la respuesta.
5. Rasa entrega la respuesta final al cliente.

## Ejemplo de llamada REST con JWT

```bash
curl -X POST "http://localhost:5005/webhooks/rest/webhook" \
  -H "Content-Type: application/json" \
  -d '{
        "sender": "mi_usuario",
        "message": "¿Qué tareas tengo?",
        "metadata": {"jwt_token": "<TOKEN_JWT>"}
      }'
```

Las acciones leen `metadata.jwt_token` y lo envían en la cabecera `Authorization: Bearer <TOKEN_JWT>` cuando llaman a FastAPI.

## Notas sobre los formularios

- `member_creation_form` y `member_update_form` validan entradas básicas (correo, rol, IDs numéricos).
- `create_task_comment_form` y `update_task_comment_form` validan IDs y URLs de imágenes.
- Las acciones de confirmación (`action_confirm_*`) existen para cerrar los formularios y mostrar mensajes al usuario.

## Próximos pasos sugeridos

- Ajustar las URL (`API_BASE` y `BASE_URL` en `actions/actions.py`) si FastAPI vive en otra red o con HTTPS.
- Implementar lógica adicional de autorización/decodificación de roles usando el JWT antes de llamar a los servicios de FastAPI.
- Añadir más ejemplos en `data/nlu.yml` para mejorar la cobertura de intents.

## Guía de pruebas manuales (mensajes y resultados esperados)

> Requisitos previos: entorno virtual activado, dependencias instaladas, `es_core_news_md` descargado, FastAPI corriendo en `http://127.0.0.1:8000` con una base de datos válida y un usuario existente para generar el JWT.

1. **Entrenar el modelo**

   ```bash
   rasa train --config config.yml --domain domain.yml --data data
   ```

   - Resultado esperado: se genera un archivo `models/*.tar.gz` sin errores.

2. **Levantar servicios en dos terminales**

   - Servidor de acciones (usa el JWT que llegue en la metadata):

     ```bash
     rasa run actions --actions chatbot.actions.actions --port 5055
     ```

     - Resultado esperado: consola mostrando `Action endpoint is up` y solicitudes entrantes por cada acción.

   - Servidor Rasa:

     ```bash
     rasa run --enable-api --port 5005 --endpoints endpoints.yml --credentials credentials.yml
     ```

     - Resultado esperado: mensajes de arranque sin errores; listo para recibir eventos REST.

3. **Obtener un JWT desde FastAPI**

   ```bash
   curl -X POST "http://127.0.0.1:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "usuario@demo.com", "password": "<clave>"}'
   ```

   - Resultado esperado: JSON con `access_token` (p. ej. `{"access_token": "<JWT>", "token_type": "bearer"}`).

4. **Probar intenciones básicas** (usar el token en `metadata.jwt_token`):

   ```bash
   curl -X POST "http://localhost:5005/webhooks/rest/webhook" \
     -H "Content-Type: application/json" \
     -d '{
           "sender": "tester",
           "message": "hola",
           "metadata": {"jwt_token": "<JWT>"}
         }'
   ```

   - Resultado esperado: `"¡Hola! Soy tu asistente de HomeTasks. ¿En qué te ayudo?"`.

5. **Probar consulta de tareas personales**

   ```bash
   curl -X POST "http://localhost:5005/webhooks/rest/webhook" \
     -H "Content-Type: application/json" \
     -d '{
           "sender": "tester",
           "message": "¿Qué tareas tengo?",
           "metadata": {"jwt_token": "<JWT>"}
         }'
   ```

   - Resultado esperado si FastAPI responde con tareas: texto tipo `"Tus tareas:• <titulo> - <estado>"`. Si el backend no responde, el bot devuelve `"No se pudo conectar con el servidor."`.

6. **Probar formulario de creación de miembro** (sin tocar backend real)

   - Enviar intención: `"quiero registrar un miembro"` activará las reglas de formulario y deberías ver la primera pregunta `"¿Cuál es el nombre completo del miembro?"`.
   - Responder con datos de ejemplo para cada slot:
     1. `"Juan Pérez"` → sigue al correo.
     2. `"juan@example.com"` → sigue a contraseña.
     3. `"123456"` → sigue a rol.
     4. `"1"` (rol admin) → sigue a hogar.
     5. `"10"` (ID hogar) → el formulario llama a FastAPI y responde `"Miembro creado correctamente."` si el backend lo permite.

7. **Probar formulario de comentario en tarea**

   - Mensaje inicial: `"quiero dejar un comentario a mi tarea"` → pregunta `"¿Qué ID de tarea quieres usar?"`.
   - Proveer `task_id`, `member_id`, `comment_text` y opcional `comment_image` (debe empezar con `http`).
   - Resultado esperado: `"Comentario creado correctamente."` o un mensaje de conexión si el backend no está disponible.

8. **Probar cierres de conversación**

   - Mensaje `"gracias"` → `"¡Con gusto! ¿Hay algo más que pueda hacer?"`.
   - Mensaje `"adiós"` → `"¡Hasta luego!"`.

Si necesitas verificar los datos de entrenamiento para más ejemplos de frases por intención, revisa `data/nlu.yml`.
