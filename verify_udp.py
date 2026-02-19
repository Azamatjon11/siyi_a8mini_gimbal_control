import socket
import struct
import time
import argparse

# SIYI UDP Configuration
SIYI_IP = "192.168.144.25"
SIYI_PORT = 37260

# CRC16-CCITT (Poly 0x1021, Init 0x0000)
def crc16_ccitt(data):
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

def make_packet(seq, cmd_id, payload=b''):
    # Header: 0x55 0x66 (Low byte first -> 55 66)
    stx = b'\x55\x66'
    ctrl = 1 # Need ACK
    length = len(payload)
    
    # Header body for CRC: CTRL(1) + LEN(2) + SEQ(2) + CMD(1) + DATA(N)
    body = struct.pack('<BHHB', ctrl, length, seq, cmd_id) + payload
    
    crc = crc16_ccitt(body)
    packet = stx + body + struct.pack('<H', crc)
    return packet

def test_udp():
    print(f"Creating UDP socket to {SIYI_IP}:{SIYI_PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    
    # 1. Acquire Firmware Version (CMD 0x12)
    # Payload: Empty
    seq = 1
    pkt = make_packet(seq, 0x12)
    print(f"Sending Firmware Req ({len(pkt)} bytes): {pkt.hex()}")
    
    try:
        sock.sendto(pkt, (SIYI_IP, SIYI_PORT))
        data, addr = sock.recvfrom(1024)
        print(f"SUCCESS! Received {len(data)} bytes from {addr}: {data.hex()}")
    except socket.timeout:
        print("Timeout: No response for FW Req.")
    except OSError as e:
        print(f"Network Error: {e}")
        print("Check your network settings. Is your IP in 192.168.144.x range?")

    # 2. Try Hardware ID (CMD 0x02) just in case
    # Payload: Empty
    seq += 1
    pkt = make_packet(seq, 0x02)
    print(f"\nSending Hardware ID Req ({len(pkt)} bytes): {pkt.hex()}")
    
    try:
        sock.sendto(pkt, (SIYI_IP, SIYI_PORT))
        data, addr = sock.recvfrom(1024)
        print(f"SUCCESS! Received {len(data)} bytes from {addr}: {data.hex()}")
    except socket.timeout:
        print("Timeout: No response for Hardware ID Req.")

    sock.close()

if __name__ == "__main__":
    test_udp()
