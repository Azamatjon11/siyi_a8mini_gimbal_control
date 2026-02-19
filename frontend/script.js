const ws = new WebSocket(`ws://${location.host}/ws/control`);
const statusEl = document.getElementById('status-indicator');
const logContainer = document.getElementById('log-container');

// Fetch Ports
async function loadPorts() {
    try {
        const res = await fetch('/api/ports');
        const data = await res.json();
        const datalist = document.getElementById('port-list');
        datalist.innerHTML = '';
        data.ports.forEach(port => {
            const opt = document.createElement('option');
            opt.value = port;
            datalist.appendChild(opt);
        });
        if (data.ports.length > 0) {
            document.getElementById('port-input').value = data.ports[0];
        }
    } catch (e) {
        log("Failed to load ports: " + e);
    }
}
loadPorts();

// State
let isConnected = false;
let currentSpeed = 50;

function log(msg) {
    const div = document.createElement('div');
    div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    logContainer.prepend(div);
    if (logContainer.childElementCount > 50) logContainer.lastChild.remove();
}

ws.onopen = () => {
    log("WebSocket Connected");
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'state') {
        const state = msg.payload;
        if (state.connected !== isConnected) {
            isConnected = state.connected;
            statusEl.textContent = isConnected ? "Connected" : "Disconnected";
            statusEl.className = `status ${isConnected ? 'online' : 'offline'}`;
            log(isConnected ? "Driver Connected" : "Driver Disconnected");
        }
        document.getElementById('last-ack').textContent = state.last_ack_ts ? new Date(state.last_ack_ts * 1000).toLocaleTimeString() : 'Never';
        document.getElementById('error-count').textContent = state.errors;
    }
};

ws.onclose = () => {
    log("WebSocket Disconnected. Reconnecting...");
    setTimeout(() => location.reload(), 3000);
};

// UI Handlers
document.getElementById('btn-connect').onclick = async () => {
    const port = document.getElementById('port-input').value;
    const baud = parseInt(document.getElementById('baud-select').value);

    if (!port) {
        log("Error: Please select or enter a serial port.");
        return;
    }

    // Determine if connecting or disconnecting
    // For now simple connect
    const res = await fetch('/api/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port, baud })
    });
    const data = await res.json();
    if (res.status !== 200) {
        log(`Error: ${data.detail || 'Connection failed'}`);
    } else {
        log(`Connect req: ${data.status}`);
    }
};

document.getElementById('speed-slider').oninput = (e) => {
    currentSpeed = e.target.value;
    document.getElementById('speed-val').textContent = currentSpeed;
};

// Gimbal Control (Hold to Move)
const sendMove = (yaw, pitch) => {
    log(`UI: Move ${yaw}, ${pitch} @ ${currentSpeed}%`);
    ws.send(JSON.stringify({
        type: 'gimbal_rate',
        yaw: yaw,
        pitch: pitch,
        speed: parseInt(currentSpeed)
    }));
};

const stopMove = () => {
    ws.send(JSON.stringify({
        type: 'gimbal_rate',
        yaw: 0,
        pitch: 0,
        speed: 0
    }));
};

const setupHold = (id, yaw, pitch) => {
    const btn = document.getElementById(id);
    // Mouse
    btn.onmousedown = () => sendMove(yaw, pitch);
    btn.onmouseup = stopMove;
    btn.onmouseleave = stopMove;
    // Touch
    btn.ontouchstart = (e) => { e.preventDefault(); sendMove(yaw, pitch); };
    btn.ontouchend = (e) => { e.preventDefault(); stopMove(); };
};

setupHold('btn-up', 0, 1);
setupHold('btn-down', 0, -1);
setupHold('btn-left', -1, 0);
setupHold('btn-right', 1, 0);

document.getElementById('btn-center').onclick = async () => {
    await fetch('/api/gimbal/center', { method: 'POST' });
};

document.getElementById('btn-stop').onclick = async () => {
    await fetch('/api/gimbal/stop', { method: 'POST' });
};

// Camera Control
const setupZoom = (id, dir) => {
    const btn = document.getElementById(id);
    const start = () => ws.send(JSON.stringify({ type: 'zoom', action: dir }));
    const stop = () => ws.send(JSON.stringify({ type: 'zoom', action: 'stop' }));

    btn.onmousedown = start;
    btn.onmouseup = stop;
    btn.onmouseleave = stop;
    btn.ontouchstart = (e) => { e.preventDefault(); start(); };
    btn.ontouchend = (e) => { e.preventDefault(); stop(); };
};

setupZoom('btn-zoom-in', 'in');
setupZoom('btn-zoom-out', 'out');

document.getElementById('btn-photo').onclick = async () => {
    await fetch('/api/camera/photo', { method: 'POST' });
};

document.getElementById('btn-record').onclick = async () => {
    await fetch('/api/camera/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'toggle' })
    });
};
