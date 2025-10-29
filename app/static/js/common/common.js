import {AlertPopup} from "./popup.js";

// The data returned should contain:
// status and msg: show a popup message
// or data: opqaue and should be handled by the calling module
const __handle_fetch = async resp => {
    const data = await resp.json();
    if (data && "status" in data) {
        new AlertPopup(data.status, data.msg);
        return null;
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