import {AlertPopup} from "./popup.js";

// The data returned should contain:
// status and msg: show a popup message
// or data: opqaue and should be handled by the calling module
const __handle_fetch = async resp => {
    const data = await resp.json();
    if (data.status) {
        new AlertPopup(data.status, data.msg);
        delete data.status;
        delete data.msg;
        if (Object.keys(data).length === 0) return null
        return data;
    }
    return data
}

export const fetch_post = async (endpoint, body, raw_body=false) => {
    if (!raw_body) body = JSON.stringify(body);
    const response = await fetch(Flask.url_for(endpoint), {method: 'POST', body});
    return __handle_fetch(response);
}

export const fetch_update = async (endpoint, body) => {
    const response = await fetch(Flask.url_for(endpoint), {method: 'UPDATE', body: JSON.stringify(body),});
    return __handle_fetch(response);
}

export const fetch_get = async (endpoint, args = {}) => {
    const response = await fetch(Flask.url_for(endpoint, args));
    return __handle_fetch(response);
}

export const fetch_delete = async (endpoint, args) => {
    const response = await fetch(Flask.url_for(endpoint, args), {method: "DELETE"});
    return __handle_fetch(response);
}

export const form_default_set = (defaults) => {
    for (const def of defaults) {
        const field = document.getElementById(def.id);
        if (def.type === "select") {
            field.innerHTML = "";
            for (const option of def.options) {
                const o = document.createElement("option");
                o.label = option.label;
                o.value = option.value;
                o.selected = (def.default || null) === option.value;
                field.appendChild(o);
            }
        }
    }
}

let busy_indicator = [];

export function busy_indication_on() {
    // document.querySelector(".busy-indicator").style.display = "block";
    const indicator = document.createElement("div");
    indicator.classList.add("busy-indicator");
    document.querySelector("main").appendChild(indicator);
    busy_indicator.push(indicator);
}

export function busy_indication_off() {
    // document.querySelector(".busy-indicator").style.display = "none";
    for (const indicator of busy_indicator) indicator.remove();
    busy_indicator = [];
}

export const now_iso_string = () => {
    const now = new Date();
    const iso_now = now.toJSON().substring(0, 19).replace(/T../, ` ${now.getHours()}`);
    return iso_now
}

// To make sure the client reloads when the server is rebooted, different mechanisms are implemented.
// On a development server (no webserver), the fetch throws an exception which is handled in the catch
// On a webserver, the fetch returns a status 502
// On a webserver, if the service is restarted (sudo systemctl restart service-name), this can happen so fast that the client does not perceive it correctly,
// i.e. the socketio is interrupted but it is not noticed by the catch or the 502.
// Therefore, the hb returns a timestamp from the server, which is changed each time the server reboots.  If the client notices the timestamp has changed, it reloads.
// At development time, when the server is restarted and the page is reloaded, avoid loading the page twice by setting skip_reload=true
let popup_alert = null;
export const __check_server_alive_loop = async (skip_reload=false) => {
    try {
        const ret = await fetch(Flask.url_for('api.hb'), {signal: AbortSignal.timeout(2000)});
        if (ret.status in [502, 504]) throw new Error(); // server says: bad gateway
        const status = await ret.json();
        if (localStorage.getItem("reboot") === "true" || localStorage.getItem("hb-timestamp") !== status.hb.toString()) {
            localStorage.setItem("reboot", "false");
            localStorage.setItem("hb-timestamp", status.hb);
            if (!skip_reload) location.reload();
             if (popup_alert) {
                 popup_alert.hide();
                 popup_alert = null;
             }
        }
    } catch  {
        localStorage.setItem("reboot", "true");
        if (!popup_alert) popup_alert = new AlertPopup("warning", "Systeem buiten dienst, even geduld aub...", 0);
    }
    setTimeout(__check_server_alive_loop, 3000);
};

export const check_server_alive = async () => {
    __check_server_alive_loop(true);
}
