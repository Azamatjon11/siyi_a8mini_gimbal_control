import serial
import time
import struct
import argparse
import itertools

# CRC Implementations
def crc16_ccitt_init_0(data):
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

def crc16_ccitt_init_ffff(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
        crc &= 0xFFFF
    return crc

def make_packet(seq, cmd_id, payload=b'', header_val=0x6655, crc_func=crc16_ccitt_init_0):
    # Header: Low byte first (Little Endian)
    # If header_val is 0x6655 -> b'\x55\x66'
    stx = struct.pack('<H', header_val)
    
    ctrl = 1 # Need ACK
    length = len(payload)
    
    # Header body for CRC: CTRL(1) + LEN(2) + SEQ(2) + CMD(1) + DATA(N)
    # LEN, SEQ are Little Endian
    body = struct.pack('<BHHB', ctrl, length, seq, cmd_id) + payload
    
    crc = crc_func(body)
    packet = stx + body + struct.pack('<H', crc)
    return packet

def test_config(ser, header, crc_name, crc_func):
    print(f"Testing Header={hex(header)}, CRC={crc_name}...", end='', flush=True)
    
    # Try Acquire Firmware (0x12)
    pkt = make_packet(1, 0x12, b'', header_val=header, crc_func=crc_func)
    ser.write(pkt)
    time.sleep(0.2)
    if ser.in_waiting:
        resp = ser.read(ser.in_waiting)
        print(f" RESPONSE! {resp.hex()}")
        return True
    
    # Try Acquire Hardware ID (0x02)
    pkt = make_packet(2, 0x02, b'', header_val=header, crc_func=crc_func)
    ser.write(pkt)
    time.sleep(0.2)
    if ser.in_waiting:
        resp = ser.read(ser.in_waiting)
        print(f" RESPONSE! {resp.hex()}")
        return True
        
    print(" No response.")
    return False

def main(port):
    bauds = [115200, 57600]
    headers = [0x6655, 0x5566]
    crcs = [("Init 0", crc16_ccitt_init_0), ("Init FFFF", crc16_ccitt_init_ffff)]
    
    for baud in bauds:
        print(f"\n--- Checking Baud {baud} ---")
        try:
            ser = serial.Serial(port, baud, timeout=0.1)
        except Exception as e:
            print(f"Failed to open {baud}: {e}")
            continue
            
        for header, (crc_name, crc_func) in itertools.product(headers, crcs):
            if test_config(ser, header, crc_name, crc_func):
                print(f"\nSUCCESS FOUND! Baud={baud}, Header={hex(header)}, CRC={crc_name}")
                ser.close()
                return
        
        ser.close()
    
    print("\nNo working configuration found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="Serial port")
    args = parser.parse_args()
    main(args.port)
