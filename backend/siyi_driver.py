import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any, List
import serial_asyncio
import serial
from .siyi_protocol import SiyiPacket

logger = logging.getLogger(__name__)

class SiyiDriver:
    def __init__(self):
        self.transport = None
        self.protocol = None
        self.connected = False
        self.port = ""
        self.baud = 115200
        
        self.seq = 0
        self.ack_futures: Dict[int, asyncio.Future] = {}  # seq -> Future
        self.state: Dict[str, Any] = {
            "connected": False,
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "zoom_state": "unknown",
            "record_state": "unknown",
            "last_ack_ts": 0,
            "retries": 0,
            "errors": 0
        }
        self._stop_event = asyncio.Event()
        self._read_task = None
        self._heartbeat_task = None

    async def connect(self, port: str, baud: int = 115200):
        if self.connected:
            await self.disconnect()
            
        self.port = port
        self.baud = baud
        
        try:
            loop = asyncio.get_running_loop()
            self.transport, self.protocol = await serial_asyncio.create_serial_connection(
                loop, 
                lambda: SerialProtocol(self._on_packet_received),
                port, 
                baudrate=baud
            )
            self.connected = True
            self.state["connected"] = True
            self._stop_event.clear()
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info(f"Connected to {port} at {baud}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.state["errors"] += 1
            raise e

    async def disconnect(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self.transport:
            self.transport.close()
        self.connected = False
        self.state["connected"] = False
        logger.info("Disconnected")

    def _on_packet_received(self, packet: SiyiPacket):
        # Handle ACKs
        if packet.is_ack:
            # Check seq in futures
            if packet.seq in self.ack_futures:
                fut = self.ack_futures.pop(packet.seq)
                if not fut.done():
                    fut.set_result(packet)
            self.state["last_ack_ts"] = time.time()
        
        # Handle Data Packets (e.g. status)
        self._parse_state_packet(packet)

    def _parse_state_packet(self, packet: SiyiPacket):
        # Command ID 0x0D (13) is often status or similar, or specific ID?
        # Based on research:
        # Acquire Attitude Data ID: 0x16 (22)
        # Gimbal Status Information ID: 0x0F (15)
        
        # Assuming we get Attitude Data (ID 22)
        if packet.cmd_id == 22: # Attitude
            # Payload validation needed. Assuming standard float/int packing
            pass 
        elif packet.cmd_id == 15: # Status
            pass

    async def send_cmd(self, cmd_id: int, payload: bytes = b'', expect_ack: bool = True, timeout: float = 1.0, retries: int = 3) -> bool:
        if not self.connected:
            return False
            
        for attempt in range(retries + 1):
            self.seq = (self.seq + 1) % 65536
            seq = self.seq
            
            packet = SiyiPacket(seq=seq, cmd_id=cmd_id, payload=payload, need_ack=expect_ack)
            encoded = packet.encode()
            
            if expect_ack:
                fut = asyncio.get_running_loop().create_future()
                self.ack_futures[seq] = fut
                
            try:
                self.transport.write(encoded)
                if not expect_ack:
                    return True
                
                await asyncio.wait_for(fut, timeout)
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for ACK (seq={seq}, attempt={attempt+1})")
                self.state["retries"] += 1
                if seq in self.ack_futures:
                    del self.ack_futures[seq]
            except Exception as e:
                logger.error(f"Error sending command: {e}")
                self.state["errors"] += 1
                return False
                
        return False

    async def _heartbeat_loop(self):
        while self.connected:
            try:
                # Send Acquire FW Version or Gimbal Status as heartbeat
                # CMD ID 0x12 (18) = Acquire Firmware Version
                await self.send_cmd(18, b'', expect_ack=True, timeout=2.0)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(1.0) # 1Hz

class SerialProtocol(asyncio.Protocol):
    def __init__(self, packet_callback: Callable[[SiyiPacket], None]):
        self.callback = packet_callback
        self.buffer = bytearray()
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.buffer.extend(data)
        self._process_buffer()

    def _process_buffer(self):
        while True:
            packet, consumed = SiyiPacket.decode(self.buffer)
            if consumed == 0:
                break
            
            # Remove consumed bytes
            # Note: consumed can be 1 (invalid header) or full packet len
            del self.buffer[:consumed]
            
            if packet:
                self.callback(packet)
