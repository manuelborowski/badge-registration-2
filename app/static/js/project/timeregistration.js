import {check_server_alive, fetch_post} from "../common/common.js";
import {rfid_serial} from "../common/rfidserial.js";

$(document).ready(async function () {
    document.addEventListener("visibilitychange", () => {
    });
    __update_clock();
    __reload_page();
    check_server_alive();
    __scanner_init();
});

const __update_clock = () => {
    const now = new Date();
    const options = {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',};
    document.querySelector("#clock").innerHTML = `${now.toLocaleDateString('nl-BE', options)} ${now.toLocaleTimeString('nl-BE')}`;
    setTimeout(__update_clock, 1000);
}

let __logged_once = false;
// reload the page at certain moments to reset the socketio connections
const __reload_page = () => {
    const today = new Date().toDateString();
    const now = Date.now();
    let moments = reload_page_moments.map(m => Date.parse(`${today} ${m} GMT+1`)).sort();
    moments.push(moments[0] + 24 * 3600 * 1000);  // first moment is added at end with 24 hours added to handle array overflow
    let stored_moment = parseInt(localStorage.getItem("reload_page_at"));
    if (stored_moment === null || !moments.includes(stored_moment)) { // Not stored yet, store the first (earliest) moment
        localStorage.setItem("reload_page_at", moments[0]);
        stored_moment = moments[0];
    }
    if (!__logged_once) {
        console.log(`Next reload at ${new Date(stored_moment)}`);
        __logged_once = true;
    }
    if (now >= stored_moment) {
        const next_moment = moments.filter(m => m > now)[0];
        localStorage.setItem("reload_page_at", next_moment);
        location.reload();
    }
    setTimeout(__reload_page, 1000 * 10);
}

const __scanner_init = () => {
    rfid_serial.connect(async data => {
        if (data.type === "state") {
        } else if (data.type === "rfid") {
            await fetch_post("registration.registration", {location_key: "timeregistration", rfid: data.rfid, timestamp: (new Date()).toJSON().substring(0, 19)})
        }
    });

}