class SerialViaWebSocket {
    __cb = null;
    ws = null;
    ws_state = false;
    serial_admin = false;
    serial_oper = false;
    previous_state = null;
    reconnect_timer = null;
    reconnect_delay = 500;
    max_reconnect_delay = 10000;

    constructor() {
        this.open_socket();
    }

    open_socket = () => {
        if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) return;

        const ws = new WebSocket("wss://localhost:8765/ws");
        this.ws = ws;
        ws.onmessage = (e) => {
            let data;
            try {
                data = JSON.parse(e.data);
            } catch (error) {
                console.error("Invalid RFID websocket message", error, e.data);
                return;
            }

            if ("read" in data) {
                if (this.__cb) this.__cb({type: "rfid", rfid: data.read.code, timestamp: data.read.timestamp.substring(0, 19), hostname: data.read.hostname});
            } else if ("scanner_state" in data) {
                this.set_state({serial_oper: data.scanner_state.state});
            } else {
                console.log("ws.onmessage, unknown data", data);
            }
        };
        ws.onerror = () => this.set_state({ws_state: false, serial_oper: false});
        ws.onopen = () => {
            if (this.ws !== ws) return;
            this.reconnect_delay = 500;
            this.set_state({ws_state: true});
            ws.send(JSON.stringify({status: this.serial_admin}));
        };
        ws.onclose = () => {
            if (this.ws !== ws) return;
            this.set_state({ws_state: false, serial_oper: false});
            this.schedule_reconnect();
        };
    }

    schedule_reconnect = () => {
        if (this.reconnect_timer !== null) return;
        const delay = this.reconnect_delay;
        this.reconnect_delay = Math.min(this.reconnect_delay * 2, this.max_reconnect_delay);
        this.reconnect_timer = setTimeout(() => {
            this.reconnect_timer = null;
            this.open_socket();
        }, delay);
    }

    set_state = ({ws_state, serial_admin, serial_oper} = {}) => {
        if (ws_state !== undefined) this.ws_state = ws_state;
        if (serial_admin !== undefined) this.serial_admin = serial_admin;
        if (serial_oper !== undefined) this.serial_oper = serial_oper;
        const state = this.ws_state && this.serial_oper && this.serial_admin;
        if (state !== this.previous_state) {
            this.previous_state = state;
            if (this.__cb) this.__cb({type: "state", value: state});
        }
    }

    // callback = {type, data...}
    // type: state, value: false or true
    // type: rfid, rfid: rfid-code, timestamp: now()
    connect = async (cb = null) => {
        this.__cb = cb;
        this.set_state({serial_admin: true});
        if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({status: true}));
        else this.open_socket();
    }

    disconnect = async () => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({status: false}));
        this.set_state({serial_admin: false});
        this.__cb = null;
    }
}

export const rfid_serial = new SerialViaWebSocket();
