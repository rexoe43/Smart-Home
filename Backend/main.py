# Smart-Home (Alexa+)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Callable, Literal, Optional
import json
import re
import logging

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("smart-home")

#Global state of the home
home_state: Dict[str, Any] = {
    "living_room_light": "off",
    "thermostat_temp": 22,
    "front_door": "closed",
    "air_conditioner": "off",
}

#FASTAPI
app = FastAPI(
    title="Smart Home API",
    description="Backend para Alexa+",
    version="1.0.0",
)

@app.post("/alexa-webhook")
async def alexa_webhook(request: Request):
    payload = await request.json()
    intent_name = payload.get("request", {}).get("intent", {}).get("name")

    if intent_name == "ControlDispositivoIntent":
        mensaje = "Comando recibido: Apagando la televisión"
    else:
        mensaje = "Hola, comando genérico recibido"
    
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": "Conexión exitosa"
            },
            "shouldEndSession": True
        }
    }

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tools cape
class ControlLightArgs(BaseModel):
    """Argumentos para controlar la luz de la sala"""
    state: Literal["on", "off"] = Field(
        ..., description="Estado deseado de la luz: 'on' o 'off'"
    )

class AdjustTemperatureArgs(BaseModel):
    """Argumentos para ajustar la temperatura"""
    target_temp: int = Field(
        ..., ge=10, le=35,
        description="Temperatura deseada en grados Celsius"
    )

class GetHomeStatusArgs(BaseModel):
    """No requiere Argumentos"""
    pass

# Tools implementation
def control_living_room_light(state: str) -> Dict[str, Any]:
    """Enciende o apaga la luz de la sala"""
    home_state["living_room_light"] = state
    return {
        "tool": "conrol_living_room_light",
        "result": f"Luz de la sala {'encendida' if state == 'on' else 'apagada'}",
        "state": home_state.copy()
    }

def adjust_temperature(target_temp: int) -> Dict[str, Any]:
    """Modificar la temperatura del termostato"""
    home_state["thermostat_temp"] = target_temp
    return {
        "tool": "adjust_temperature",
        "result": f"Temperatura ajustada a {target_temp}°C",
        "state": home_state.copy()
    }

def get_home_status() -> Dict[str, Any]:
    """Devuelve el estado actual de la casa"""
    return {
        "tool": "get_home_status",
        "result": "Estado actual de la casa obtenido",
        "state": home_state.copy()
    }

# Tools registration
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "control_living_room_light": {
        "schema": ControlLightArgs,
        "func": control_living_room_light,
    },
    "adjust_temperature": {
        "schema": AdjustTemperatureArgs,
        "func": adjust_temperature,
    },
    "get_home_status": {
        "schema": GetHomeStatusArgs,
        "func": get_home_status,
    },
}

# Lenguage interperter
def interpret_command(user_message: str) -> Dict[str, Any]:
    """
    Interpreta un comando en lenguaje natural y devuelve la herramienta
    """
    msg = user_message.lower().strip()

    # Luz de la sala
    if any(k in msg for k in ["luz", "light", "lampara", "lámpara"]):
        if any(k in msg for k in ["enciende", "encender", "prende", "on", "activar"]):
            return {"tool": "control_living_room_light", "args": {"state": "on"}}
        if any(k in msg for k in ["apaga", "apagar", "off", "desactivar"]):
            return {"tool": "control_living_room_light", "args": {"state": "off"}}

    # Termostato
    if any(k in msg for k in ["temperatura", "termostato", "grados", "clima"]):
        match = re.search(r"(\d{1,2})", msg)
        if match:
            temp = int(match.group(1))
            if 10 <= temp <= 35:
                return {"tool": "adjust_temperature", "args": {"target_temp": temp}}

    # Estado general
    if any(k in msg for k in ["estado", "status", "como esta", "cómo esta", "resumen"]):
        return {"tool": "get_home_status", "args": {}}

    # Comando no reconocido
    return {"tool": None, "args": {}}

# Tools executer
def execute_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida y ejecuta la herramienta correspondiente
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "tool": tool_name,
            "error": f"Herramienta '{tool_name}' no registrada",
            "state": home_state.copy(),
        }

    entry = TOOL_REGISTRY[tool_name]
    schema = type[BaseModel] = entry["schema"]
    func: Callable = entry["func"]

    try:
        validated = schema(**args)
        return func(**validated.model_dump())
    except Exception as e:
        logger.exception("Error ejecutando herramienta %s", tool_name)
        return {
            "tool": tool_name,
            "error": f"Error al ejecutar '{tool_name}': {str(e)}",
            "state": home_state.copy(),
        }

# Models for response with HTTP
class StatusResponse(BaseModel):
    """Respuesta del endpoint"""
    state: Dict[str, Any]

class ToolInfo(BaseModel):
    """Información de la herramienta"""
    name: str
    description: str
    schema: Dict[str, Any]

# Endpoints

@app.get("/")
async def root():
    return {"message": "Smart Home Activada", "status": "online"}

@app.get("/api/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Devuelve el estado actual de la casa"""
    return StatusResponse(state=home_state.copy())

@app.get("/api/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    """Lista todas las herramientas disponibles"""
    tools = []
    for name, entry in TOOL_REGISTRY.items():
        schema_cls: type[BaseModel] = entry["schema"]
        tools.append(
            ToolInfo(
                name=name,
                description=(schema_cls.__doc__ or "").strip(),
                schema=schema_cls.model_json_schema(),
            )
        )
    return tools

@app.get("/health")
async def health() -> Dict[str, str]:
    """Endpoint de salud del servidor"""
    return {"status": "ok"}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Canal de comunicación en tiempo real con el cliente"""
    await websocket.accept()
    logger.info("Cliente conectado al WebSocket: %s", websocket.client)

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

            logger.info("Comado recibido: %s", user_message)

            intent = interpret_command(user_message)

            if intent["tool"]:
                result = execute_tool(intent["tool"], intent["args"])
                if "error" in result:
                    response_text = f"{result['error']}"
                else:
                    response_text = f"{result.get('result', 'Acción ejecutada')}"
            else:
                response_text = (
                    "No he entendido el comando"
                    "'enciende la luz de la sala'\n"
                    "'apaga la luz'\n"
                    "'pon el termostato a 24 grados'\n"
                    "'dame el estado de la casa'"
                )

                await websocket.send_json({
                    "response": response_text,
                    "state": home_state.copy(),
                })

    except WebSocketDisconnect:
        logger.info("Cliente desconectado: %s", websocket.client)
    except Exception as e:
        logger.exception("Error en el websocket")
        try:
            await websocket.send_json({
                "response": f"Error interno del servidor: {str(e)}",
                "state": home_state.copy(),
            })
        except Exception:
            pass

# Execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)