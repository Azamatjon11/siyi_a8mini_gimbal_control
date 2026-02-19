import serial
import time
import struct
import argparse

# CRC16-CCITT (0x1021)
def calculate_crc(data):
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

def make_packet(seq, cmd_id, payload=b'', header_ver=1):
    # Header V1: 0x55 0x66
    # Header V2: 0x66 0x55
    
    if header_ver == 1:
        stx = b'\x55\x66'
    else:
        stx = b'\x66\x55'
        
    ctrl = 1 # Need ACK
    length = len(payload)
    
    # Header body for CRC: CTRL(1) + LEN(2) + SEQ(2) + CMD(1) + DATA(N)
    # LEN, SEQ are Little Endian
    body = struct.pack('<BHHB', ctrl, length, seq, cmd_id) + payload
    
    crc = calculate_crc(body)
    packet = stx + body + struct.pack('<H', crc)
    return packet

def test_protocol(port, baud):
    print(f"Opening {port} at {baud}...")
    try:
        ser = serial.Serial(port, baud, timeout=0.5)
    except Exception as e:
        print(f"Error opening port: {e}")
        return

    # Test 1: Header 0x55 0x66 (Standard), CMD: Acquire FW (18)
    print("\n--- Test 1: Header 0x55 0x66, CMD: Acquire FW ---")
    pkt = make_packet(1, 18, b'', header_ver=1)
    print(f"Sending: {pkt.hex()}")
    ser.write(pkt)
    resp = ser.read(100)
    print(f"Recv: {resp.hex()}")
    if resp:
        print("SUCCESS? Received data!")

    # Test 2: Header 0x66 0x55 (Reversed), CMD: Acquire FW (18)
    print("\n--- Test 2: Header 0x66 0x55, CMD: Acquire FW ---")
    pkt = make_packet(2, 18, b'', header_ver=2)
    print(f"Sending: {pkt.hex()}")
    ser.write(pkt)
    resp = ser.read(100)
    print(f"Recv: {resp.hex()}")
    if resp:
         print("SUCCESS? Received data!")

    # Test 3: Rotation (Header 1)
    # CMD 3 (Right) for 1 second
    print("\n--- Test 3: Rotate Right (Speed 20) with Header 1 ---")
    payload = struct.pack('B', 20)
    pkt = make_packet(3, 3, payload, header_ver=1)
    print(f"Sending: {pkt.hex()}")
    ser.write(pkt)
    time.sleep(1)
    
    # Stop
    print("Sending Stop")
    pkt = make_packet(4, 5, b'', header_ver=1)
    ser.write(pkt)
    resp = ser.read(100) # Check for ACKs
    print(f"Recv: {resp.hex()}")

    ser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="Serial port (e.g. /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()
    
    test_protocol(args.port, args.baud)
