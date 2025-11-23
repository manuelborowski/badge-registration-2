class RfidSerialWorker {
    __write_interval = null;
    __connect_interval = null;
    __admin_state = false;

    __disconnect_eventhandler() {
        this.parent.__port.removeEventListener("disconnect", this.__disconnect_eventhandler);
        if (this.parent.__write_interval) {
            clearInterval(this.parent.__write_interval);
            this.parent.__write_interval = null;
        }
        this.parent.__connect_interval = setInterval(() => {
            if (this.parent.__admin_state) this.parent.connect();
        }, 2000);
        postMessage({type: "state", value: false})

    }

    async __connect_eventhandler() {
        this.parent.__port.removeEventListener("connect", this.__connect_eventhandler);
        if (this.parent.__admin_state) await this.parent.connect();
    }

    async connect() {
        const ports = await navigator.serial.getPorts();
        if (ports.length > 0) {
            this.__port = ports[0];
            this.__port.parent = this;
            this.__admin_state = true;
            await this.__port.open({baudRate: 115200});
            this.__writer = this.__port.writable.getWriter();
            this.__reader = this.__port.readable.getReader();

            await this.start_polling();
            // await this.readLoop();

            this.__port.addEventListener("disconnect", this.__disconnect_eventhandler);

            this.__port.addEventListener("connect", this.__connect_eventhandler);

            if (this.__connect_interval) {
                clearInterval(this.__connect_interval);
                this.__connect_interval = null;
            }
            postMessage({type: "state", value: true})
        }
    }

    async disconnect() {
        this.__admin_state = false;
        try {
            this.__reader?.cancel();
            this.__reader?.releaseLock();
        } catch (e) {
            console.log("error canceling reader", e);
        }
        try {
            this.__writer?.releaseLock();
        } catch (e) {
            console.log("error canceling writer", e);
        }
        try {
            await this.__port?.close();
        } catch (e) {
            console.log("error close", e);
        }
        if (this.__connect_interval) {
            clearInterval(this.__connect_interval);
            this.__connect_interval = null;
        }
        if (this.__write_interval) {
            clearInterval(this.__write_interval);
            this.__write_interval = null;
        }
    }

    static SAME_RFID_DELAY = 20; // = x 10 seconds delay before same rfid can be scanned again
    async start_polling() {
        const data = new Uint8Array(new Uint8Array([0xab, 0xba, 0x00, 0x10, 0x00, 0x10]));
        let prev_rfid = null;
        let delay_ctr = RfidSerialWorker.SAME_RFID_DELAY;
        this.__write_interval = setInterval(async () => {
            try {
                await this.__writer.write(data);
                const {value, done} = await this.__reader.read();
                if (done || !value) clearInterval(this.__write_interval);
                if (value[3] === 0x81) {
                    const rfid = value.slice(5, 9).toHex().toUpperCase();
                    if ((prev_rfid !== rfid || delay_ctr <= 0) && rfid.length === 8) {
                        prev_rfid = rfid;
                        delay_ctr = RfidSerialWorker.SAME_RFID_DELAY;
                        postMessage({type: "rfid", rfid, timestamp: new Date()})
                    } else {
                        delay_ctr--;
                    }
                }
            } catch (err) {
                console.log("Write error: " + err.message);
            }
        }, 100);
    }
}

const worker = new RfidSerialWorker()
onmessage = (event) => {
    if (event.data.type === "connect") worker.connect();
    if (event.data.type === "disconnect") worker.disconnect();
};
