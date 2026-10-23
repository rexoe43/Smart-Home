# Smart Home Alexa+

Plataforma integral de domótica inteligente que sincroniza el control del hogar en tiempo real a través de la voz mediante una **Skill de Amazon Alexa** y una interfaz web interactiva (**Frontend en React**).

---

## Descripción de la Arquitectura

El sistema funciona bajo un esquema centralizado y reactivo:

```text
       [ Amazon Alexa (Voz) ]
                 │ (HTTPS POST / JSON)
                 ▼
          [ ngrok Tunnel ]
                 │
                 ▼
       ┌────────────────────────────────────────────────────────┐
       │             Backend (FastAPI en Python)                │
       │  • Webhook Alexa (/alexa-webhook)                      │
       │  • Intérprete NLU (interpret_command)                  │
       │  • Herramientas domóticas (execute_tool)               │
       │  • ConnectionManager (Broadcast por WebSockets)        │
       │  • Endpoints REST (/api/status, /history, /api/tools)  │
       └────────────────────────────────────────────────────────┘
                 ▲                                ▲
                 │ (HTTP REST)                    │ (WebSocket Bidireccional /ws)
                 └────────────────┬───────────────┘
                                  │
                       [ Frontend Web (React + Vite) ]
                        • Dashboard interactivo
                        • Asistente de chat
                        • Actualización en tiempo real
```

1. **Amazon Alexa Skill:** Captura la voz del usuario, extrae las intenciones (_Intents_) y valores (_Slots_), y los envía mediante un webhook HTTPS al backend.
2. **ngrok:** Publica de forma segura el servidor local de FastAPI con un túnel HTTPS compatible con los requerimientos SSL de Amazon.
3. **Backend (FastAPI):** Núcleo lógico que procesa tanto las órdenes de Alexa como los comandos recibidos desde la web, ejecuta las herramientas domóticas y emite la actualización de estado a todos los clientes conectados vía **WebSockets**.
4. **Frontend (React + Vite):** Panel de control moderno con micro-interacciones que refleja al instante el estado de los dispositivos (luces, termostato, puerta principal) y mantiene sincronizado el chat con las respuestas emitidas por Alexa.

---

## Componentes del Sistema

### 1. Backend (`FastAPI + WebSockets`)

- **FastAPI:** Framework web asíncrono de alto rendimiento encargado de los endpoints REST y del webhook de Alexa.
- **WebSockets (`/ws`):** Canal de comunicación full-duplex gestionado por `ConnectionManager` para difundir cambios de estado de forma instantánea al navegador.
- **Pydantic:** Validación estricta de esquemas de datos y parámetros de las herramientas domóticas.
- **Uvicorn:** Servidor ASGI para ejecutar la aplicación asíncrona en Python.

### 2. Frontend (`React + Vite`)

- **React 18+:** Construcción de componentes reactivos y gestión de estado local (`home_state`, historial de chat, conexión).
- **Vite:** Empaquetador ultrarrápido y servidor de desarrollo.
- **Lucide React:** Iconografía estilizada y moderna para los dispositivos y métricas.
- **Vanilla CSS:** Diseño responsivo con estética moderna, tipografías _DM Sans_ y _Manrope_, y microanimaciones fluidas.

### 3. Alexa Custom Skill

- **Nombre de invocación:** `smart home`
- **Intents configurados:**
  - `ControlDispositivoIntent`: Manejo de encendido/apagado de luces, puerta y temperatura.
  - `AMAZON.StopIntent` y `AMAZON.CancelIntent`: Salida de la sesión.
- **Slots:**
  - `estado` (`AMAZON.SearchQuery` o personalizado): Captura verbos y acciones (`prender`, `apagar`, `abrir`, `cerrar`).
  - `temperatura` (`AMAZON.NUMBER`): Captura valores numéricos de grados para el clima.

---

## Comandos de Voz y Chat Soportados

| Comando                                     | Acción en el Hogar           | Respuesta del Asistente               |
| :------------------------------------------ | :--------------------------- | :------------------------------------ |
| **"Prende la luz"** / **"Enciende la luz"** | Enciende la luz de la sala   | _"Luz de la sala encendida"_          |
| **"Apaga la luz"**                          | Apaga la luz de la sala      | _"Luz de la sala apagada"_            |
| **"Pon la temperatura a (x) grados"**       | Ajusta el termostato a `x`°C | _"Temperatura ajustada a X°C"_        |
| **"Baja la temperatura a (x) grados"**      | Reduce o fija el termostato  | _"Temperatura ajustada a X°C"_        |
| **"Abre la puerta"**                        | Destraba la puerta principal | _"Puerta principal abierta"_          |
| **"Cierra la puerta"**                      | Asegura la puerta principal  | _"Puerta principal cerrada"_          |
| **"Dame el estado de la casa"**             | Consulta general de sensores | Resumen completo del estado del hogar |

---

## Estructura del Proyecto

```text
Smart-Home/
├── Backend/
│   └── main.py              # Servidor FastAPI, endpoints REST, WebSocket y Webhook de Alexa
├── Frontend/
│   ├── index.html           # Plantilla base HTML5
│   ├── package.json         # Dependencias y scripts de Node.js
│   ├── vite.config.js       # Configuración de Vite
│   └── src/
│       ├── App.jsx          # Componente principal (Dashboard, controles y chat)
│       ├── main.jsx         # Punto de entrada de React
│       └── styles.css       # Estilos globales y responsive design
├── .gitignore
├── README.md                # Documentación del proyecto
└── package-lock.json
```

---

## Paquetes y Tecnologías Utilizadas

### Python (Backend)

- `fastapi`: Framework para API REST y WebSockets.
- `uvicorn`: Servidor ASGI para producción y desarrollo.
- `pydantic`: Modelos de datos y tipado estático.
- `websockets`: Protocolo de comunicación en tiempo real.

### Node.js (Frontend)

- `react`: Biblioteca para construir interfaces de usuario.
- `react-dom`: Renderizado en el DOM de React.
- `vite`: Entorno y servidor de desarrollo para frontend.
- `lucide-react`: Paquete de iconos.

### Servicios Externos

- **Amazon Alexa Developer Console:** Plataforma para la creación y entrenamiento del modelo de interacción NLU de la Skill.
- **ngrok:** Exposición segura de endpoints locales mediante túneles públicos HTTPS con certificado SSL wildcard.

---

## Instalación y Ejecución Local

### Prerrequisitos

- **Python 3.10+**
- **Node.js 18+** y **npm**
- **Cuenta en ngrok** con el cliente instalado y autenticado
- **Cuenta en Amazon Alexa Developer Console**

---

### Paso 1: Configurar y Ejecutar el Backend

1. Abre una terminal y sitúate en la raíz del proyecto:
   ```bash
   cd Smart-Home
   ```
2. Activa tu entorno virtual de Python:
   - **Windows (PowerShell):**
     ```powershell
     .\.venv\Scripts\Activate
     ```
   - **Linux / macOS:**
     ```bash
     source .venv/bin/activate
     ```
3. Instala las dependencias requeridas si aún no las tienes:
   ```bash
   pip install fastapi uvicorn pydantic websockets
   ```
   o más rápido
   ```bash
   pip install -r requirements.txt
   ```
5. Navega a la carpeta del Backend y arranca el servidor:
   ```bash
   cd Backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   _El backend estará disponible en `http://localhost:8000`._

---

### Paso 2: Exponer el Backend con ngrok (para Alexa)

En otra terminal, corre ngrok apuntando al puerto de FastAPI:

```bash
ngrok http 127.0.0.1:8000
```

Copia la URL pública generada que comience con `https://` (ejemplo: `https://xxxx-xxxx.ngrok-free.dev`).

---

### Paso 3: Configurar el Endpoint en Alexa Developer Console

1. Entra a tu skill en [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
2. Ve a la pestaña **Build** $\rightarrow$ **Endpoint** (menú izquierdo).
3. Selecciona la opción **HTTPS**.
4. En **Default Region**, pega la URL de ngrok agregando `/alexa-webhook`:
   ```text
   https://tu-subdominio.ngrok-free.dev/alexa-webhook
   ```
5. En el menú desplegable del certificado SSL, selecciona:
   > _"My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"_
6. Haz clic en **Save Endpoints**.
7. En la pestaña **Build**, asegúrate de hacer clic en **Build Model** y esperar a que finalice.

---

### Paso 4: Ejecutar el Frontend

En una tercera terminal:

1. Ve a la carpeta `Frontend`:
   ```bash
   cd Frontend
   ```
2. Instala las dependencias de Node.js:
   ```bash
   npm install
   ```
3. Inicia el servidor de desarrollo:
   ```bash
   npm run dev
   ```
4. Abre tu navegador en la URL indicada (habitualmente `http://localhost:5173`).

---

## Pruebas de Funcionamiento

1. Abre el Frontend en el navegador (`http://localhost:5173`).
2. Ve a la consola de Alexa $\rightarrow$ pestaña **Test**.
3. Escribe o di por micrófono:
   ```text
   abre smart home
   ```
4. Envía cualquier orden, por ejemplo:
   ```text
   apaga la luz
   pon la temperatura a 26 grados
   abre la puerta
   ```
5. Observa cómo Alexa responde por voz/texto y **simultáneamente el Dashboard web y el chat se actualizan en tiempo real**.
