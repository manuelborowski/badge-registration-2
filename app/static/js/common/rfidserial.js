class RfidSerial {
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

export const rfid_serial = new RfidSerial();