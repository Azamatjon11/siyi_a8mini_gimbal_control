# SIYI Gimbal Connection Troubleshooting

If the verification script failed on all baud rates, the issue is likely **Physical Connection**.

## The Issue: USB-C Port vs UART Port
The **USB-C port** on the side of the SIYI A8 Mini is often dedicated to **Firmware Updates** and **Configuration** via the SIYI PC Assistant. It usually **does not** accept SDK control commands (like Rotate).

Your `lsusb` output:
`ID 0483:5740 STMicroelectronics Virtual COM Port`
This confirms you are connected to the internal STM32 chip via USB-C, but this port is likely in "Maintenance Mode".

## The Solution: Use the UART/Control Port

To control the gimbal with this software, you almost certainly need to connect to the **UART Interface**.

### 1. Hardware Required
- **USB-to-TTL Adapter** (e.g., CP2102, FTDI, CH340).
- **SIYI Control Cable** (usually included, connects to the small port labeled "Control" or "UART").

### 2. Wiring
| SIYI UART Cable | USB-TTL Adapter |
|-----------------|-----------------|
| **TX**          | **RX**          |
| **RX**          | **TX**          |
| **GND**         | **GND**         |
| VCC (Optional)  | *Do not connect unless powering gimbal via USB* |

### 3. Verify
1. Unplug the direct USB-C cable.
2. Plug in the USB-TTL adapter.
3. Run `lsusb` or `ls /dev/tty*`. You should see a new device (e.g., `/dev/ttyUSB0` or `/dev/ttyACM0`).
4. Run the verification script again on this new port:
   ```bash
   python3 verify_protocol_bruteforce.py /dev/ttyUSB0
   ```

## Alternative: Ethernet
If you have the Ethernet cable, the SIYI A8 Mini also accepts SDK commands via UDP (IP: 192.168.144.25, Port: 37260). This project is currently set up for Serial, but can be adapted for UDP if needed.
