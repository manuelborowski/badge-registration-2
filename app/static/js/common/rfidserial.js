class SerialViaWebSocket {
    __cb = null;
    ws = null;
    ws_state = true;
    serial_admin = false;
    serial_oper = false;
    previous_state = null;

    constructor() {
        this.ws = new WebSocket("wss://localhost:8765/ws");
        this.ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (this.__cb) {
                if ("read" in data) {
                    // this.beep.play();
                    this.__cb({type: "rfid", rfid: data.read.code, timestamp: data.read.timestamp.substring(0, 19), hostname: data.read.hostname});
                } else if ("scanner_state" in data)
                    this.set_state({serial_oper: data.scanner_state.state});
                else console.log(`ws.onmessage, unknown data ${data}`);
            }
        };
        this.ws.onerror = () => this.set_state({ws_state: false});
        this.ws.onopen = () => this.set_state({ws_state: true});
        this.ws.onclose = () => this.set_state({ws_state: false});
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
        while (this.ws.readyState === 0) await new Promise(r => setTimeout(r, 1000)); // It is not possible to access the scanner while ws is not up
        this.__cb = cb;
        if (this.ws_state) this.ws.send(JSON.stringify({status: true}))
        this.set_state({serial_admin: true})
    }

    disconnect = async () => {
        this.__cb = null;
        if (this.ws_state) await this.ws.send(JSON.stringify({status: false}))
        this.set_state({serial_admin: false})
    }
}

export const rfid_serial = new SerialViaWebSocket();
