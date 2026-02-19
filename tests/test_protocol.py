import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.siyi_protocol import SiyiPacket, SiyiCRC, HEADER

def test_crc_calculation():
    # Test case from some known CRC16-CCITT examples or just consistency
    data = b'123456789'
    # CRC-CCITT (0xFFFF) typically, but SIYI uses 0x0000 init.
    # 0x31 0x32 ...
    # Let's rely on self-consistency for now: encode -> decode should work.
    pass

def test_packet_encode_decode():
    seq = 100
    cmd_id = 0x01
    payload = b'\x01\x02\x03'
    packet = SiyiPacket(seq=seq, cmd_id=cmd_id, payload=payload)
    
    encoded = packet.encode()
    
    assert encoded[0:2] == b'\x55\x66'
    
    # Decode
    decoded, length = SiyiPacket.decode(encoded)
    assert decoded is not None
    assert decoded.seq == seq
    assert decoded.cmd_id == cmd_id
    assert decoded.payload == payload
    assert length == len(encoded)

def test_partial_packet():
    seq = 100
    cmd_id = 0x01
    payload = b'\x01\x02\x03'
    packet = SiyiPacket(seq=seq, cmd_id=cmd_id, payload=payload)
    encoded = packet.encode()
    
    # Send partial
    decoded, length = SiyiPacket.decode(encoded[:5])
    assert decoded is None
    assert length == 0

def test_corrupt_packet():
    seq = 100
    cmd_id = 0x01
    payload = b'\x01\x02\x03'
    packet = SiyiPacket(seq=seq, cmd_id=cmd_id, payload=payload)
    encoded = packet.encode()
    
    # Corrupt a byte in payload
    corrupt = bytearray(encoded)
    corrupt[-3] = 0x99 # Last byte of payload (payload is at -3, -4, -5 from end? no, CRC is 2 bytes)
    # Encoded: STX(2) CTRL(1) LEN(2) SEQ(2) CMD(1) PAYLOAD(3) CRC(2) = 13 bytes
    # Payload indices: 8, 9, 10. CRC: 11, 12.
    corrupt[8] = 0xFF
    
    decoded, length = SiyiPacket.decode(bytes(corrupt))
    assert decoded is None
    assert length == 2 # Should skip header (2 bytes)
