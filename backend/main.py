import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import struct

from .siyi_driver import SiyiDriver
from .connection import ConnectionManager

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
driver = SiyiDriver()
manager = ConnectionManager()

# Pydantic Models
class ConnectRequest(BaseModel):
    port: str
    baud: int = 115200

class RecordRequest(BaseModel):
    action: str  # "start", "stop", "toggle"

# Mount Frontend (Static Files)


# Background Task for State Broadcast
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_state())

async def broadcast_state():
    while True:
        # Broadcast driver state
        state_msg = {"type": "state", "payload": driver.state}
        await manager.broadcast(state_msg)
        await asyncio.sleep(0.2)  # Update UI at 5Hz

import serial.tools.list_ports

# ...

# REST Endpoints
@app.get("/api/ports")
async def list_ports():
    ports = serial.tools.list_ports.comports()
    return {"ports": [p.device for p in ports]}

@app.post("/api/connect")
async def connect_driver(req: ConnectRequest):
    try:
        await driver.connect(req.port, req.baud)
        return {"status": "connected", "port": req.port}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/disconnect")
async def disconnect_driver():
    await driver.disconnect()
    return {"status": "disconnected"}

@app.post("/api/gimbal/center")
async def center_gimbal():
    # Command ID 0x00?? No, SDK says 0x01 is Center?
    # Research says 0 - Auto Centering
    success = await driver.send_cmd(0, b'', expect_ack=True)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send command")
    return {"status": "ok"}

@app.post("/api/gimbal/stop")
async def stop_gimbal():
    # ID 5 - Stop
    success = await driver.send_cmd(5, b'', expect_ack=True)
    return {"status": "ok"}

@app.post("/api/camera/photo")
async def take_photo():
    # ID 12 - Take Picture
    success = await driver.send_cmd(12, b'', expect_ack=True)
    return {"status": "ok"}

@app.post("/api/camera/record")
async def record_video(req: RecordRequest):
    # ID 13 - Record (Toggle)
    # The protocol only has "Record Video" (13) which usually toggles.
    # We might not be able to enforce "start" vs "stop" without checking state.
    # For now, just send the toggle command.
    success = await driver.send_cmd(13, b'', expect_ack=True)
    return {"status": "ok", "action": "toggle"}

# WebSocket Endpoint
@app.websocket("/ws/control")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "gimbal_rate":
                # {yaw: -1..1, pitch: -1..1, speed: 0..100}
                yaw = float(data.get("yaw", 0))
                pitch = float(data.get("pitch", 0))
                speed = int(data.get("speed", 50))
                
                # Discrete Control Logic
                # Yaw: -1 (Left), 1 (Right) | Pitch: 1 (Up), -1 (Down)
                # Discrete Control Logic
                # Yaw: -1 (Left), 1 (Right) | Pitch: 1 (Up), -1 (Down)
                # Payload: 1 byte for speed (0-100)
                speed_byte = struct.pack('B', speed) # Use the speed from UI
                
                if yaw == 1:
                     # Rotate Right (ID 3)
                     await driver.send_cmd(3, speed_byte, expect_ack=False)
                elif yaw == -1:
                     # Rotate Left (ID 4)
                     await driver.send_cmd(4, speed_byte, expect_ack=False)
                
                if pitch == 1:
                     # Rotate Up (ID 1)
                     await driver.send_cmd(1, speed_byte, expect_ack=False)
                elif pitch == -1:
                     # Rotate Down (ID 2)
                     await driver.send_cmd(2, speed_byte, expect_ack=False)
                     
                if yaw == 0 and pitch == 0:
                     # Stop (ID 5)
                     await driver.send_cmd(5, b'', expect_ack=False)
                
            elif msg_type == "zoom":
                # {action: "in"|"out"|"stop"}
                action = data.get("action")
                cmd_id = None
                if action == "in":
                    cmd_id = 6 # Zoom +1
                elif action == "out":
                    cmd_id = 7 # Zoom -1
                elif action == "stop":
                    # No explicit stop zoom command found in summary?
                    # Maybe send stop rotation (5) stops everything?
                    # Or just stop sending zoom commands.
                    pass
                
                if cmd_id:
                     await driver.send_cmd(cmd_id, b'', expect_ack=True)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Mount Frontend (Static Files) - Must be last to avoid capturing API/WS routes
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
if not os.path.exists(frontend_path):
    os.makedirs(frontend_path)
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
