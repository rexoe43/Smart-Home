# AGENTS.md — Arquitectura del Sistema de Asistencia (Smart Home AI)

## 1. Visión General de la Arquitectura

El backend del proyecto está construido utilizando **FastAPI** y sigue un diseño procedural/funcional modular. El sistema actúa como un puente inteligente entre los comandos de voz de **Alexa+** y los eventos en tiempo real enviados al **Frontend** mediante **WebSockets**. La lógica central se divide en tres capas principales:

* **Capa de Entrada (Webhooks / Canales):** Recibe las peticiones del simulador de Alexa y de los clientes web a través de endpoints REST (`/alexa-webhook`) y canales bidireccionales (`/ws`).
* **Capa de Interpretación (`interpret_command`):** Procesa el lenguaje natural (tanto comandos de texto como slots de voz con números en dígitos o letras), identificando la intención y los parámetros correspondientes.
* **Capa de Ejecución de Herramientas (`TOOL_REGISTRY`):** Valida los argumentos mediante esquemas de Pydantic y ejecuta de forma segura las funciones del sistema sobre el estado global del hogar.

---

## 2. Definición de Herramientas (Tools Schema & Registry)

Las capacidades del sistema están encapsuladas en herramientas autodescriptivas registradas en un diccionario central (`TOOL_REGISTRY`). Cada herramienta cuenta con validación estricta de tipos mediante **Pydantic**:

### `control_living_room_light`
* **Descripción:** Enciende o apaga la luz de la sala.
* **Argumentos:** `state` (Literal: `"on"`, `"off"`).

### `adjust_temperature`
* **Descripción:** Modifica la temperatura del termostato.
* **Argumentos:** `target_temp` (Entero validado entre 10 y 35 grados Celsius).

### `get_home_status`
* **Descripción:** Obtiene el estado consolidado de todos los dispositivos del hogar (`home_state`).
* **Argumentos:** Ninguno.

---

## 3. Flujo de Procesamiento del Asistente (Agentic Loop)

El ciclo de procesamiento de una orden sigue los siguientes pasos:

1. **Recepción del Payload:** El webhook (`/alexa-webhook`) intercepta la solicitud HTTP procedente de Alexa, extrayendo el tipo de request, el nombre del intent y los valores de los slots.
2. **Traducción Semántica:** La función de interpretación analiza la frase del usuario combinando expresiones regulares y diccionarios de conversión (por ejemplo, mapeando números escritos con letras como *"treinta"* a valores numéricos).
3. **Validación y Ejecución:** La función `execute_tool` toma la herramienta identificada y valida los parámetros contra el esquema Pydantic correspondiente antes de mutar el estado global de la casa (`home_state`).
4. **Persistencia y Auditoría:** Cada acción ejecutada genera un registro detallado en la bitácora (`action_history`) con marca de tiempo.
5. **Sincronización en Tiempo Real:** Mediante el gestor de conexiones (`ConnectionManager`), se transmite de forma asíncrona un broadcast por WebSockets hacia el Frontend, actualizando instantáneamente la interfaz visual del usuario.
