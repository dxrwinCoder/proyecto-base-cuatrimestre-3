# WhatsApp Cloud API (plantillas)

Paquete aislado para enviar notificaciones por WhatsApp desde FastAPI sin mezclar la logica con `services/`.

## Variables de entorno requeridas
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_TEMPLATE_NAME` (ej. `visita_perdida`) [se puede sobreescribir por payload]
- `WHATSAPP_TEMPLATE_LANG` (ej. `es` o `es_MX`) [se puede sobreescribir por payload]
- `WHATSAPP_API_VERSION` (opcional, por defecto `v19.0`)
- `WHATSAPP_DEFAULT_CONTACT` (opcional para {{4}})

## Endpoint
`POST /notificaciones/whatsapp/enviar`

```json
{
  "evento": "tarea_por_vencer",
  "destinatario": {
    "nombre": "John",
    "telefono": "+5215555555555",
    "rol_id": 2,
    "contacto": "support@telco.com"
  },
  "tarea": {
    "id": 123,
    "titulo": "Instalacion de banda ancha",
    "fecha_limite": "2025-12-31",
    "estado": "pendiente"
  }
}
```

Si no envias `override_variables`, el servicio usa la IA ya configurada para rellenar las variables de la plantilla. Si quieres fijarlas directamente, envia:

```json
{
  "override_variables": ["John", "Instalacion de banda ancha", "2025-12-31", "support@telco.com"]
}
```

## Eventos soportados
- `tarea_por_vencer`
- `nueva_tarea`
- `asignado_evento`
- `comentario_tarea`
- `tarea_completada`
- `tarea_vencida`
- `cambio_estado_tarea`

Cada evento ajusta el texto corto con fallback determinista si la IA falla.

## Usar una segunda plantilla (ejemplo: `recordatorio_notificacion`)
La plantilla de la captura tiene 2 variables en el cuerpo ({{1}} fecha, {{2}} hora).

Ejemplo de payload:
```json
{
  "evento": "tarea_por_vencer",
  "destinatario": {
    "nombre": "John",
    "telefono": "+5215555555555",
    "rol_id": 2
  },
  "tarea": {
    "id": 123,
    "titulo": "Tareas del evento",
    "fecha_limite": "2025-12-31"
  },
  "template_name": "recordatorio_notificacion",
  "template_language": "es",
  "variable_order": ["fecha", "hora"],
  "body_variables_expected": 2,
  "metadata": { "hora": "10:00 AM" }
}
```
El servicio arma el fallback con fecha y hora, o puedes enviar `override_variables` con 2 elementos en el orden de la plantilla.