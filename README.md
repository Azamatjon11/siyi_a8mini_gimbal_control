# SIYI A8 Mini Gimbal Web Controller

A local web application to control SIYI A8 Mini gimbal cameras via USB/Serial on Raspberry Pi (or other Linux/Mac systems).

## Features
- **Control**: Pan/Tilt (Discrete), Center, Lock Mode (Planned).
- **Camera**: Zoom In/Out, Take Photo, Record Video (Toggle).
- **Status**: Live connection status, sequence counter, error tracking.
- **Responsive UI**: Single-page dashboard optimized for mobile/desktop.

## Installation

1. Clone the repository:
   ```bash
   git clone <repo_url>
   cd siyi_gimbal_controller
   ```

2. Create virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   *Note: `requirements.txt` should contain: `fastapi uvicorn pyserial aiofiles websockets`*

## Usage

1. Connect the SIYI gimbal via USB-C to the Raspberry Pi.
2. Identify the serial port (usually `/dev/ttyACM0` or `/dev/ttyUSB0`).
3. Run the server:
   ```bash
   source venv/bin/activate
   python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
4. Open a browser and navigate to `http://<pi-ip-address>:8000`.
5. Enter the serial port (e.g., `/dev/ttyACM0`) and click **Connect**.

## Troubleshooting

- **Permissions**: Ensure your user has access to serial ports:
  ```bash
  sudo usermod -a -G dialout $USER
  ```
  (Relogin required)
- **Status "Disconnected"**: Check physical connection using `ls /dev/tty*`.
- **No Response/ACK**: 
  - Verify BaudRate (default 115200).
  - Verify Gimbal is powered on.
  - Check `dmesg` to see if device is recognized.

## Development

- **Backend**: Python 3.10+ (FastAPI)
- **Frontend**: Vanilla HTML/JS
- **Tests**: Run `pytest` to verify protocol logic.
