from mcp.server.mcpserver import MCPServer
mcp = MCPServer("Smart-Home")

smart_home_state = {
    "living_room_light": "off",
    "temperature": 22,
    "front_door" : "locked",
    "ac_status": "standby"
}

@mcp.tool()
def control_living_room_light(state: str) -> str:
    """"
    Enciende o apaga luz de la sala.
    Args:
    State: 'on' para encender, 'off' para apagar
    """
    global smart_home_state
    if state.lower() in ["on", "off"]:
        smart_home_state["living_room_light"] = state.lower()
        return f"Living room light turned {state.lower()}"
    return "Error: No válido"

@mcp.tool()
def get_home_status() -> dict:
    """Devuelve el estado actual de la casa inteligente."""
    return smart_home_state

@mcp.tool()
def adjust_temperature(new_temp: int) -> str:
    """
    Ajusta la temperatura de la casa.
    Args:
    new_temp: Nueva temperatura deseada
    """
    global smart_home_state
    smart_home_state["temperature"] = new_temp
    return f"Temperature set to {new_temp}°C"

if __name__ == "__main__":
    mcp.run()

