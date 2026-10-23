from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Callable, Literal, List
import json
import re
import logging
import asyncio

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("smart-home")

# Estado global del hogar
home_state: Dict[str, Any] = {
    "living_room_light": "off",
    "thermostat_temp": 22,
    "front_door": "closed",
    "air_conditioner": "off",
}

app = FastAPI(
    title="Smart Home API",
    description="Backend para Alexa y Frontend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

action_history: List[Dict[str, str]] = []

def registrar_evento(dispositivo: str, accion: str, resultado: str):
    """Registra las acciones ejecutadas en el historial reciente (máximo 20 eventos)."""
    evento = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device": dispositivo,
        "action": accion,
        "result": resultado
    }
    action_history.insert(0, evento)
    if len(action_history) > 20:
        action_history.pop()

class ConnectionManager:
    """Gestiona conexiones activas por WebSocket para sincronización en tiempo real."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Cliente WebSocket conectado. Conexiones activas: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Cliente WebSocket desconectado. Conexiones activas: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        """Transmite el mensaje y el estado actualizado a todos los clientes web."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for dead in disconnected:
            self.disconnect(dead)

ws_manager = ConnectionManager()

# Modelos para validación de argumentos de herramientas
class ControlLightArgs(BaseModel):
    state: Literal["on", "off"] = Field(..., description="Estado de la luz: 'on' u 'off'")

class AdjustTemperatureArgs(BaseModel):
    target_temp: int = Field(..., ge=10, le=35, description="Temperatura objetivo en grados Celsius (10 a 35)")

class ControlDoorArgs(BaseModel):
    state: Literal["open", "closed"] = Field(..., description="Estado de la puerta: 'open' o 'closed'")

class GetHomeStatusArgs(BaseModel):
    pass

# Implementación de herramientas de control del hogar
def control_living_room_light(state: str) -> Dict[str, Any]:
    home_state["living_room_light"] = state
    estado_texto = "encendida" if state == "on" else "apagada"
    return {
        "tool": "control_living_room_light",
        "result": f"Luz de la sala {estado_texto}",
        "state": home_state.copy()
    }

def adjust_temperature(target_temp: int) -> Dict[str, Any]:
    clamped = max(10, min(35, target_temp))
    home_state["thermostat_temp"] = clamped
    return {
        "tool": "adjust_temperature",
        "result": f"Temperatura ajustada a {clamped}°C",
        "state": home_state.copy()
    }

def control_door(state: str) -> Dict[str, Any]:
    home_state["front_door"] = state
    estado_texto = "abierta" if state == "open" else "cerrada"
    return {
        "tool": "control_door",
        "result": f"Puerta principal {estado_texto}",
        "state": home_state.copy()
    }

def get_home_status() -> Dict[str, Any]:
    luz = "encendida" if home_state.get("living_room_light") == "on" else "apagada"
    temp = home_state.get("thermostat_temp", 22)
    aire = "encendido" if home_state.get("air_conditioner") == "on" else "apagado"
    puerta = "abierta" if home_state.get("front_door") == "open" else "cerrada"
    resumen = (
        f"La luz de la sala está {luz}, la temperatura es de {temp} grados, "
        f"el aire está {aire} y la puerta está {puerta}."
    )
    return {
        "tool": "get_home_status",
        "result": resumen,
        "state": home_state.copy()
    }

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "control_living_room_light": {
        "schema": ControlLightArgs,
        "func": control_living_room_light,
    },
    "adjust_temperature": {
        "schema": AdjustTemperatureArgs,
        "func": adjust_temperature,
    },
    "control_door": {
        "schema": ControlDoorArgs,
        "func": control_door,
    },
    "get_home_status": {
        "schema": GetHomeStatusArgs,
        "func": get_home_status,
    },
}

def execute_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Valida los argumentos y ejecuta la herramienta indicada en el registro."""
    if tool_name not in TOOL_REGISTRY:
        return {
            "tool": tool_name,
            "error": f"Herramienta '{tool_name}' no registrada",
            "state": home_state.copy(),
        }

    entry = TOOL_REGISTRY[tool_name]
    schema: type[BaseModel] = entry["schema"]
    func: Callable = entry["func"]

    try:
        validated = schema(**args)
        return func(**validated.model_dump())
    except Exception as e:
        logger.exception("Error al ejecutar la herramienta %s", tool_name)
        return {
            "tool": tool_name,
            "error": f"Error al ejecutar '{tool_name}': {str(e)}",
            "state": home_state.copy(),
        }

def interpret_command(user_message: str) -> Dict[str, Any]:
    """
    Interpreta el lenguaje natural y devuelve la herramienta con sus argumentos.
    Soporta:
      - Luz: prender / apagar
      - Termostato: ajustar / subir / bajar temperatura
      - Puerta: abrir / cerrar
      - Estado: consultar estado del hogar
    """
    msg = user_message.lower().strip()

    # Control de puerta
    if any(k in msg for k in ["puerta", "porton", "portón"]):
        if any(k in msg for k in ["abre", "abrir", "destraba", "open"]):
            return {"tool": "control_door", "args": {"state": "open"}}
        if any(k in msg for k in ["cierra", "cerrar", "traba", "asegura", "close"]):
            return {"tool": "control_door", "args": {"state": "closed"}}

    # Control de termostato
    if any(k in msg for k in ["temperatura", "termostato", "grados", "clima"]):
        match = re.search(r"(\d{1,2})", msg)
        if match:
            return {"tool": "adjust_temperature", "args": {"target_temp": int(match.group(1))}}
        if any(k in msg for k in ["baja", "bajar", "disminuye", "enfria"]):
            current = home_state.get("thermostat_temp", 22)
            return {"tool": "adjust_temperature", "args": {"target_temp": current - 2}}
        if any(k in msg for k in ["sube", "subir", "aumenta", "calienta"]):
            current = home_state.get("thermostat_temp", 22)
            return {"tool": "adjust_temperature", "args": {"target_temp": current + 2}}

    # Consulta de estado
    if any(k in msg for k in ["estado", "status", "como esta", "cómo esta", "resumen", "que tal"]):
        return {"tool": "get_home_status", "args": {}}

    # Control de luz con mención de dispositivo
    if any(k in msg for k in ["luz", "light", "lampara", "lámpara", "foco"]):
        if any(k in msg for k in ["apaga", "apagar", "off", "desactivar"]):
            return {"tool": "control_living_room_light", "args": {"state": "off"}}
        if any(k in msg for k in ["prende", "prender", "enciende", "encender", "on", "activar"]):
            return {"tool": "control_living_room_light", "args": {"state": "on"}}

    # Acciones directas implícitas
    if any(k in msg for k in ["apaga", "apagar", "desactivar"]):
        return {"tool": "control_living_room_light", "args": {"state": "off"}}
    if any(k in msg for k in ["prende", "prender", "enciende", "encender", "activar"]):
        return {"tool": "control_living_room_light", "args": {"state": "on"}}
    if any(k in msg for k in ["abre", "abrir"]):
        return {"tool": "control_door", "args": {"state": "open"}}
    if any(k in msg for k in ["cierra", "cerrar"]):
        return {"tool": "control_door", "args": {"state": "closed"}}

    return {"tool": None, "args": {}}

@app.post("/alexa-webhook")
async def alexa_webhook(request: Request):
    """Endpoint principal para procesar peticiones y órdenes desde la skill de Alexa."""
    payload = await request.json()
    logger.info("Payload recibido de Alexa: %s", json.dumps(payload))

    req = payload.get("request", {})
    request_type = req.get("type")
    intent_data = req.get("intent", {})
    intent_name = intent_data.get("name")

    # Invocación inicial de la skill
    if request_type == "LaunchRequest":
        bienvenida = "Bienvenido a Smart Home. ¿Qué deseas realizar?"
        asyncio.create_task(ws_manager.broadcast({
            "response": f"[Alexa]: {bienvenida}",
            "state": home_state.copy()
        }))
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": bienvenida
                },
                "reprompt": {
                    "outputSpeech": {
                        "type": "PlainText",
                        "text": "¿Qué deseas hacer en Smart Home? Puedes encender la luz, fijar la temperatura o consultar el estado."
                    }
                },
                "shouldEndSession": False
            }
        }

    # Cierre de sesión de la skill
    if intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
        despedida = "Hasta luego, saliendo de Smart Home"
        return {
            "version": "1.0",
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": despedida
                },
                "shouldEndSession": True
            }
        }

    # Extracción de valores de slots
    slots = intent_data.get("slots", {})
    slot_words = []
    temp_from_slot = None

    for s_name, s_val in slots.items():
        if isinstance(s_val, dict):
            val = s_val.get("value")
            if val is not None:
                slot_words.append(str(val))
                if "temp" in s_name.lower() or str(val).isdigit():
                    try:
                        temp_from_slot = int(val)
                    except ValueError:
                        pass
            for res_auth in s_val.get("resolutions", {}).get("resolutionsPerAuthority", []):
                for item in res_auth.get("values", []):
                    name_res = item.get("value", {}).get("name")
                    if name_res:
                        slot_words.append(str(name_res))

    texto_slots = " ".join(slot_words).lower()
    intent_result = {"tool": None, "args": {}}

    # Interpretación basada en el texto de los slots
    if texto_slots:
        intent_result = interpret_command(texto_slots)

    # Clasificación por nombre de Intent si los slots no resolvieron la orden
    if not intent_result["tool"] and intent_name:
        name_lower = intent_name.lower()

        if any(k in name_lower for k in ["puerta", "door"]):
            st = "open" if any(k in texto_slots for k in ["abre", "abrir", "open"]) else "closed"
            intent_result = {"tool": "control_door", "args": {"state": st}}

        elif any(k in name_lower for k in ["temperatura", "termostato", "temperature"]):
            target = temp_from_slot or 22
            intent_result = {"tool": "adjust_temperature", "args": {"target_temp": target}}

        elif any(k in name_lower for k in ["estado", "status"]):
            intent_result = {"tool": "get_home_status", "args": {}}

        elif "controldispositivo" in name_lower or "luz" in name_lower:
            if temp_from_slot is not None:
                intent_result = {"tool": "adjust_temperature", "args": {"target_temp": temp_from_slot}}
            elif any(k in texto_slots for k in ["apaga", "apagar", "off", "desactiv"]):
                intent_result = {"tool": "control_living_room_light", "args": {"state": "off"}}
            elif any(k in texto_slots for k in ["prende", "enciende", "activar", "on"]):
                intent_result = {"tool": "control_living_room_light", "args": {"state": "on"}}
            elif any(k in texto_slots for k in ["puerta", "cerrar", "abre", "open", "close"]):
                st = "open" if any(k in texto_slots for k in ["abre", "open"]) else "closed"
                intent_result = {"tool": "control_door", "args": {"state": st}}
            elif any(k in texto_slots for k in ["temperatura", "grados", "clima", "termostato"]):
                intent_result = {"tool": "adjust_temperature", "args": {"target_temp": 24}}
            elif any(k in texto_slots for k in ["estado", "status", "resumen"]):
                intent_result = {"tool": "get_home_status", "args": {}}

    # Ejecución de la acción identificada
    if intent_result["tool"]:
        result = execute_tool(intent_result["tool"], intent_result["args"])
        if "error" in result:
            mensaje = result["error"]
        else:
            mensaje = result.get("result", "Comando ejecutado correctamente")
            registrar_evento(intent_result["tool"], str(intent_result["args"]), mensaje)
    else:
        mensaje = (
            "No comprendí la acción. Puedes decir: Prende la luz, Apaga la luz, "
            "Pon la temperatura a 24 grados, Abre la puerta, o Dame el estado de la casa."
        )

    # Sincronización en tiempo real con el frontend por WebSocket
    asyncio.create_task(ws_manager.broadcast({
        "response": mensaje,
        "state": home_state.copy()
    }))

    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": mensaje
            },
            "reprompt": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": "¿Deseas realizar otra petición?"
                }
            },
            "shouldEndSession": False
        }
    }

@app.get("/history")
async def get_history():
    """Devuelve el historial reciente de eventos del sistema."""
    return {"history": action_history}

class StatusResponse(BaseModel):
    state: Dict[str, Any]

class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

@app.get("/")
async def root():
    return {"message": "Smart Home Activada", "status": "online"}

@app.get("/api/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Devuelve el estado actual de los dispositivos de la casa."""
    return StatusResponse(state=home_state.copy())

@app.get("/api/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    """Lista las herramientas registradas con su esquema JSON."""
    tools = []
    for name, entry in TOOL_REGISTRY.items():
        schema_cls: type[BaseModel] = entry["schema"]
        tools.append(
            ToolInfo(
                name=name,
                description=(schema_cls.__doc__ or "").strip(),
                parameters=schema_cls.model_json_schema(),
            )
        )
    return tools

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Canal WebSocket bidireccional para el frontend en tiempo real."""
    await ws_manager.connect(websocket)

    await websocket.send_json({
        "response": "Conexión establecida.",
        "state": home_state.copy(),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                user_message = payload.get("message", "")
            except json.JSONDecodeError:
                user_message = raw

            if not user_message or not user_message.strip():
                continue

            logger.info("Comando recibido por WebSocket: %s", user_message)
            intent = interpret_command(user_message)

            if intent["tool"]:
                result = execute_tool(intent["tool"], intent["args"])
                if "error" in result:
                    response_text = f"{result['error']}"
                else:
                    response_text = f"{result.get('result', 'Acción ejecutada')}"
                    registrar_evento(intent["tool"], str(intent["args"]), response_text)
            else:
                response_text = (
                    "No he entendido el comando. Puedes probar con:\n"
                    "• 'prende la luz' o 'apaga la luz'\n"
                    "• 'pon la temperatura a 24 grados'\n"
                    "• 'baja la temperatura a 20 grados'\n"
                    "• 'dame el estado de la casa'\n"
                    "• 'abre la puerta' o 'cierra la puerta'"
                )

            await ws_manager.broadcast({
                "response": response_text,
                "state": home_state.copy(),
            })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.exception("Error en el websocket")
        ws_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
