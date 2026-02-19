import struct
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

# Constants
HEADER = 0x6655  # Low byte 0x55, High byte 0x66 (0x6655 as LE is 55 66)
MIN_PACKET_LEN = 10  # STX(2) + CTRL(1) + LEN(2) + SEQ(2) + CMD(1) + CRC(2)

@dataclass
class SiyiPacket:
    seq: int
    cmd_id: int
    payload: bytes = b''
    need_ack: bool = False
    is_ack: bool = False

    def encode(self) -> bytes:
        """
        Encodes the packet into bytes according to SIYI SDK protocol.
        Format: STX(2) CTRL(1) Data_len(2) SEQ(2) CMD_ID(1) DATA(N) CRC16(2)
        STX is 0x5566 (0x55 then 0x66)
        """
        stx_bytes = struct.pack('<H', HEADER)  # 0x55, 0x66
        
        ctrl = 0
        if self.need_ack:
            ctrl |= 1
        if self.is_ack:
            ctrl |= 2
            
        length = len(self.payload)
        # Length is 2 bytes, little endian
        
        # Header part for CRC calculation: CTRL + Data_len + SEQ + CMD_ID + DATA
        # Note: STX is NOT included in CRC16 calculation usually, but SIYI docs say:
        # "CRC16 is calculated from CTRL to DATA."
        
        header_body = struct.pack('<BHHB', ctrl, length, self.seq, self.cmd_id)
        content = header_body + self.payload
        
        crc = SiyiCRC.calculate(content)
        return stx_bytes + content + struct.pack('<H', crc)

    @classmethod
    def decode(cls, data: bytes) -> Tuple[Optional['SiyiPacket'], int]:
        """
        Tries to decode a packet from the buffer.
        Returns (packet, bytes_consumed).
        If no full packet found, returns (None, 0).
        If invalid, skips 1 byte.
        """
        if len(data) < MIN_PACKET_LEN:
            return None, 0
            
        # Check Header
        stx = struct.unpack('<H', data[0:2])[0]
        if stx != HEADER:
            # Shift buffer by 1 to find next potential header
            return None, 1
            
        ctrl = data[2]
        length = struct.unpack('<H', data[3:5])[0]
        
        expected_total_len = MIN_PACKET_LEN + length
        if len(data) < expected_total_len:
            # Not enough data yet
            return None, 0
            
        # Extract content for CRC check
        content_end = expected_total_len - 2
        content = data[2:content_end]
        received_crc = struct.unpack('<H', data[content_end:expected_total_len])[0]
        
        calculated_crc = SiyiCRC.calculate(content)
        if calculated_crc != received_crc:
            # CRC failed, skip header and try again
            return None, 2 
            
        # Parse fields
        seq = struct.unpack('<H', data[5:7])[0]
        cmd_id = data[7]
        payload = data[8:content_end]
        
        packet = cls(
            seq=seq,
            cmd_id=cmd_id,
            payload=payload,
            need_ack=bool(ctrl & 1),
            is_ack=bool(ctrl & 2)
        )
        return packet, expected_total_len


class SiyiCRC:
    """
    CRC16-CCITT implementation for SIYI SDK.
    Poly: 0x1021
    Initial value: 0x0000
    """
    @staticmethod
    def calculate(data: bytes) -> int:
        crc = 0x0000
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
            crc &= 0xFFFF
        return crc
