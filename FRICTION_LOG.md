# Friction Log - Smart Home Alexa+

Este documento registra los desafíos técnicos más significativos encontrados durante el desarrollo e integración de la skill de Alexa, el backend en FastAPI y el frontend interactivo, junto con las soluciones implementadas para resolverlos.

---

## 1. Cierre Prematuro de la Sesión en Alexa

### El reto
Al principio, cada vez que Alexa recibía un comando o realizaba una invocación inicial, respondía de forma estática y cerraba la sesión inmediatamente. Esto generaba una mala experiencia de usuario, ya que obligaba a repetir *"Abre Smart Home"* antes de cada acción individual.

### Cómo lo resolvimos
Configuramos correctamente la estructura JSON de respuesta del webhook asegurándonos de enviar `"shouldEndSession": False` en conjunto con un bloque de `reprompt`. Esto permite mantener el canal conversacional abierto y fluida la interacción con el usuario, cerrando la sesión únicamente cuando el usuario solicita explícitamente salir (`AMAZON.StopIntent` o `AMAZON.CancelIntent`).

---

## 2. Sincronización en Tiempo Real entre la Voz (Alexa) y la Web (Frontend)

### El reto
Queríamos que cualquier orden dada a través del asistente de voz se reflejara instantáneamente de forma visual en el panel de control web, sin necesidad de recargar la página ni depender de peticiones periódicas por sondeo (*polling*) lento.

### Cómo lo resolvimos
Implementamos un gestor de conexiones con WebSockets (`ConnectionManager`) en FastAPI. Cada vez que el webhook de Alexa procesa un intent o una herramienta domótica:
1. Se actualiza el estado global de la casa (`home_state`).
2. El servidor ejecuta un `ws_manager.broadcast(...)` que empuja tanto la respuesta del asistente como el nuevo estado a todos los clientes web conectados al instante.
3. El frontend actualiza de inmediato los interruptores, el clima, el sensor de la puerta y el hilo de mensajes del chat.

---

## 3. Interpretación Flexible de Comandos y Parámetros (Slots / Textos)

### El reto
El simulador de la consola de desarrollo de Alexa a veces enviaba los comandos como intents personalizados, como texto plano o utilizando números escritos con letras (por ejemplo, *"treinta"* en lugar de *30*), lo que provocaba que las funciones de validación tradicionales fallaran o arrojaran errores de mapeo en los slots.

### Cómo lo resolvimos
Diseñamos una función de interpretación híbrida (`interpret_command`) con expresiones regulares y diccionarios de conversión semántica en español. Esto permite que el backend:
* Soporte tanto números en dígitos como en palabras clave (como *"treinta"*, *"veinticuatro"*, etc.).
* Maneje palabras de estado y acciones equivalentes como *"apaga"*, *"enciende"*, *"abre"* o *"cierra"* sin importar el formato exacto de entrada ni si el slot llegó vacío o desestructurado.
* Aplique un fallback inteligente que previene caídas y responde de forma asistida al usuario.
