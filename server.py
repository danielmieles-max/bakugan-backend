import asyncio
import json
import serial
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUERTO_SERIAL = "COM3"
BAUD_RATE = 115200

# VARIABLES GLOBALES COMPARTIDAS (Singleton)
ser = None
ultimo_dato = {"bakugan1": 0}  # Guarda el último estado conocido

# Tarea en segundo plano para leer el hardware de forma independiente
async def mantener_lectura_serial():
    global ser, ultimo_dato
    print(f"Intentando conectar al hardware en {PUERTO_SERIAL}...")
    
    while True:
        if ser is None or not ser.is_open:
            try:
                ser = serial.Serial(PUERTO_SERIAL, BAUD_RATE, timeout=0.1)
                ser.flush()
                print(f"¡Conexión serial exitosa y estable en {PUERTO_SERIAL}!")
            except Exception as e:
                print(f"Esperando liberación de {PUERTO_SERIAL}... (Cierra el monitor de Arduino si está abierto). Error: {e}")
                await asyncio.sleep(2)
                continue

        try:
            if ser.in_waiting > 0:
                linea = ser.readline().decode('utf-8').strip()
                try:
                    # Validamos y actualizamos el estado global
                    ultimo_dato = json.loads(linea)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"Error de lectura física: {e}")
            if ser:
                ser.close()
            ser = None

        await asyncio.sleep(0.01)

# Arrancar la lectura serial apenas encienda FastAPI
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(mantener_lectura_serial())

@app.websocket("/ws/game")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("¡Una pestaña de React se ha acoplado al bus de datos!")
    
    estado_anterior = None
    try:
        while True:
            # Enviamos el dato a React solo si cambió para no saturar la red, 
            # o de forma constante cada 50ms
            await websocket.send_json(ultimo_dato)
            await asyncio.sleep(0.05)  # Transmisión fluida de 20Hz
            
    except WebSocketDisconnect:
        print("Una pestaña de React se cerró. Bus de hardware intacto.")
    except Exception as e:
        print(f"Conexión de red finalizada: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)