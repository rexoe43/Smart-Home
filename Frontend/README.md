# Smart Home Frontend

Panel de control construido con React y Vite. Se conecta al backend FastAPI por HTTP y WebSocket.

## Inicio local

1. Inicia el backend en `http://localhost:8000`.
2. Desde esta carpeta instala dependencias y levanta Vite:

   ```bash
   npm install
   npm run dev
   ```

3. Abre la dirección que muestra Vite (normalmente `http://localhost:5173`).

El frontend usa `http://localhost:8000` por defecto. Para otra dirección, copia `.env.example` a `.env` y cambia `VITE_API_URL`.

## Funciones conectadas

- Consulta periódica de `/api/status`.
- Comandos de texto mediante `/ws`.
- Control de luz y ajuste del termostato desde el panel.
- Indicador de conexión y reconexión automática del WebSocket.
