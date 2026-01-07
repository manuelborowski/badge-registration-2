class SerialViaChrome {
    __cb = null;
    beep = null;

    constructor() {
        this.__worker = new Worker("/static/js/common/rfidserialworker.js");
        this.__worker.onmessage = (event) => {
            if (this.__cb) {
                if (event.data.type === "rfid") this.beep.play();
                this.__cb(event.data);
            }
        };
        this.beep = new Audio("static/sound/short-censor-beep.wav")
    }

    // callback = {type, data...}
    // type: state, value: false or true
    // type: rfid, rfid: rfid-code, timestamp: now()
    connect = async (cb = null) => {
        this.__cb = cb;
        // Check if page has already access to the usb port.  If so, use it.
        const ports = await navigator.serial.getPorts();
        if (ports.length > 0) {
            console.log("Using existing serial port.");
            this.__worker.postMessage({type: "connect"});
        } else {
            // Request new port, filtered by vendor/product IDs
            bootbox.confirm(
                "Open een USB poort voor de badgereader<br>Klik op <b>OK</b> en een volgend scherm verschijnt.<br>" +
                "Selecteer <b>USB2.0-Serial (ttyUSB0)</b> en klik op <b>Connect</b>",
                async result => {
                    if (result) {
                        await navigator.serial.requestPort({filters: [{usbVendorId: 0x1A86, usbProductId: 0x7523}],});
                        console.log("User selected a serial port.");
                        this.__worker.postMessage({type: "connect"});
                    }
                });
        }
    }

    disconnect = async () => {
        this.__worker.postMessage({type: "disconnect"});
    }
}

class SerialViaWebSocket {
    __cb = null;
    beep = null;
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
        // this.beep = new Audio("static/sound/short-censor-beep.wav")
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
// export const rfid_serial = new SerialViaChrome();