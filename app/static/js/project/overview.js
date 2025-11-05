import {FilterMenu} from "../common/filter_menu.js";
import {base_init} from "../base.js";
import {fetch_get, busy_indication_off, busy_indication_on} from "../common/common.js";
import {rfid_serial} from "../common/rfidserial.js";
import {ActionMenu} from "../common/action_menu.js";
import {socketio} from "../common/socketio.js";
import {person_image} from "../../img/base64-person.js";
import {datatables_init} from "../datatables/dt.js";

const meta = await fetch_get("overview.meta");

let __filters = {location: null, view_layout: null, period: null};

// rules (per location) define how a registration is processed; do nothing, add color, add tickbox...
let rules_cache = null;
const __create_rules = () => {
    rules_cache = {"=": [], "<": [], ">": []}
    if ("regel" in meta.location[__filters.location]) meta.location[__filters.location].regel.forEach(r => rules_cache[r.operator].push({limit: r.limiet, rule: r}));
}

const __check_rules = (nbr) => {
    if (rules_cache["="].length) for (const rule of rules_cache["="]) if (nbr === rule.limit) return rule.rule;
    if (rules_cache["<"].length) for (const rule of rules_cache["<"]) if (nbr < rule.limit) return rule.rule;
    if (rules_cache[">"].length) for (const rule of rules_cache[">"]) if (nbr > rule.limit) return rule.rule;
    return null
}

const canvas_element = document.getElementById("canvas");
let canvas_container = null;

const __table_template = {
    timeregistration: {header: ["Naam", "Code", "Tijd in", "Startuur", "Verschil", "Tijd uit", "Einduur", "Verschil", "Dagverschil", "Opmerking"]},
    verkoop: {header: ["Tijdstempel", "Naam", "Klas"]},
    sms: {header: ["Tijdstempel", "Naam", "Klas", "SMS", "Opmerking"]},
    cellphone: {header: ["Tijdstempel", "Naam", "Klas", "Bericht", "Aantal",]},
    toilet: {header: ["Tijdstempel", "Naam", "Klas", "Aantal",]},
}

const __photo_size_factor = 50;
// called by the server when the list of registrations is changed, i.e. one or more items (registrations) are added or removed, or a new list is displayed
const __socketio_update_list = (type, data) => {
    const view_tile = __filters.view_layout === "tile";
    const table_template = __table_template[meta.location[__filters.location].type]
    // Create table headers
    if (!view_tile) {
        let header = document.createElement("tr");
        header.dataset.sort_on = "1";
        const th = document.createElement("th");
        th.innerHTML = "<td><input class='select-all' type='checkbox' ''}></td>";
        header.appendChild(th);
        for (const item of table_template.header) {
            const th = document.createElement("th");
            th.innerHTML = item;
            header.appendChild(th);
        }
        canvas_container.prepend(header);
        document.querySelector(".select-all").addEventListener("change", e => {
            [...document.querySelectorAll(".item-select:enabled")].map(i => i.checked = e.target.checked)
        });
    }
    if (data.action === "add") {
        for (const item of data.data) {
            let registration_container = null;
            if (view_tile) {
                registration_container = document.createElement("figure");
                registration_container.style.display = "inline-block";
                registration_container.style.marginRight = "10px";
                registration_container.style.zIndex = "1";
                let src = "data:image/jpeg;base64," + (item.photo !== "" ? item.photo : person_image);
                let image = document.createElement('img');
                image.src = src;
                image.width = (2 * __photo_size_factor).toString();
                let figcaption = document.createElement("figcaption");
                figcaption.innerHTML = "(" + item.registration.time_in.split(" ")[1] + ") " + item.person.klascode + "<br>" + item.person.naam + " " + item.person.voornaam;
                figcaption.style.fontSize = (1.5 * __photo_size_factor / 100).toString() + "rem";
                figcaption.style.fontWeight = "bold";
                figcaption.style.textAlign = "center";
                registration_container.appendChild(image);
                registration_container.appendChild(figcaption);
            } else {
                registration_container = document.createElement("tr");
                registration_container.innerHTML = `
                            <td><input class="item-select" type="checkbox" ""}></td>
                            <td>${item.registration.time_in}</td>
                            <td data-col="name">${item.naam} ${item.voornaam}</td>
                            <td>${item.klascode}</td>`
                if (meta.location[__filters.location].type === "sms") {
                    registration_container.innerHTML += `
                                <td data-col="sms">${item.sms_sent ? "verstuurd" : "niet verstuurd"}</td> 
                                <td  class="edit-input" data-col="remark" data-remark-ack="${item.remark_ack}">${item.remark}</td>`;
                    if (item.remark_ack) {
                        registration_container.style.background = "palegreen"
                    }
                } else if (meta.location[__filters.location].type === "cellphone") {
                    const rule = __check_rules(item.sequence_ctr);
                    registration_container.innerHTML += `
                                <td data-col="message">${rule ? item.message_sent ? "verstuurd" : "niet verstuurd" : "NVT"}</td> 
                                <td>${item.sequence_ctr}</td>`;
                    if (rule) {
                        if (rule.kleur !== "")
                            registration_container.style.background = rule.kleur;
                    } else {
                        registration_container.firstElementChild.firstChild.disabled = true;
                    }
                } else if (meta.location[__filters.location].type === "toilet") {
                    registration_container.innerHTML += `<td>${item.sequence_ctr}</td>`;
                } else if (meta.location[__filters.location].type === "timeregistration") {
                    const time_delta_timestamp_in = Date.parse(item.timestamp.split(" ")[0] + ` ${item.startuur}:00`) - Date.parse(item.timestamp);
                    const time_delta_in = new Date(Math.abs(time_delta_timestamp_in));
                    const delta_string_in = `${time_delta_timestamp_in < 0 ? "-" : "&nbsp;"}${(time_delta_in.getHours() - 1).toString().padStart(2, "0")}:${time_delta_in.getMinutes().toString().padStart(2, "0")}:${time_delta_in.getSeconds().toString().padStart(2, "0")}`
                    let delta_string_out = "";
                    let delta_string = "";
                    if (item.time_out !== "") {
                        const time_delta_timestamp_out = Date.parse(item.time_out) - Date.parse(item.timestamp.split(" ")[0] + ` ${item.einduur}:00`);
                        const time_delta_out = new Date(Math.abs(time_delta_timestamp_out));
                        delta_string_out = `${time_delta_timestamp_out < 0 ? "-" : "&nbsp;"}${(time_delta_out.getHours() - 1).toString().padStart(2, "0")}:${time_delta_out.getMinutes().toString().padStart(2, "0")}:${time_delta_out.getSeconds().toString().padStart(2, "0")}`
                        const time_delta_timestamp = time_delta_timestamp_in + time_delta_timestamp_out;
                        const time_delta = new Date(Math.abs(time_delta_timestamp));
                        delta_string = `${time_delta_timestamp < 0 ? "-" : "&nbsp;"}${(time_delta.getHours() - 1).toString().padStart(2, "0")}:${time_delta.getMinutes().toString().padStart(2, "0")}:${time_delta.getSeconds().toString().padStart(2, "0")}`
                    }
                    registration_container.innerHTML = `
                            <td><input class="item-select" type="checkbox" ""}></td>
                            <td data-col="name">${item.naam} ${item.voornaam}</td>
                            <td>${item.klascode}</td>
                            <td>${item.timestamp}</td><td>${item.startuur}</td><td>${delta_string_in}</td>
                            <td data-col="time-out">${item.time_out}</td><td>${item.einduur}</td><td>${delta_string_out}</td>
                            <td>${delta_string}</td>
                            <td class="edit-input">${item.info}</td>
                            `
                }
            }
            registration_container.classList.add("S" + item.leerlingnummer);
            registration_container.dataset.id = item.id;
            registration_container.dataset.name = `${item.naam} ${item.voornaam}`;
            registration_container.dataset.sort_on = 100000 - item.id;
            for (const container of canvas_container.childNodes) {
                if (registration_container.dataset.sort_on < container.dataset.sort_on) {
                    container.before(registration_container);
                    break
                }
            }
            registration_container.querySelectorAll(".edit-input").forEach(td => {
                td.addEventListener("click", e => {
                    const input = document.createElement("input");
                    input.type = "text";
                    input.value = e.target.innerHTML;
                    e.target.innerHTML = "";
                    e.target.appendChild(input);
                    input.focus();
                    e.target.addEventListener("change", async e => {
                        const td = e.target.closest("td");
                        const ids = [td.closest("tr").dataset.id];
                        const ret = await fetch(Flask.url_for('api.registration_update'), {
                            headers: {'x-api-key': api_key,}, method: 'POST', body: JSON.stringify({ids, location_key: meta.location[__filters.location], fields: {info: e.target.value}}),
                        });
                        const status = await ret.json();
                        if (!status.status) bootbox.alert(status.data);
                        td.innerHTML = e.target.value;
                    })
                });
            });
        }
    } else if (data.action === "delete") {
        data.data.forEach(item => {
            const figure = document.querySelector(`[data-id="${item.id}"]`);
            if (figure) {
                figure.remove();
            }
        });
    }
    busy_indication_off();
}

// Trigger the server to send a list of all registrations
const __request_list_of_registrations_for_current_location = () => {
    busy_indication_on();
    const view_tile = __filters.view_layout === "tile";
    canvas_element.innerHTML = "";
    // Add dummy element to indicate end of list
    if (view_tile) {
        canvas_container = document.createElement("div");
        const sentinel = document.createElement("div");
        sentinel.dataset.sort_on = "zz";
        canvas_container.appendChild(sentinel);
    } else {
        canvas_container = document.createElement("table")
        canvas_container.style.margin = "auto";
        const last_row = document.createElement("tr");
        last_row.dataset.sort_on = "zz";
        canvas_container.appendChild(last_row);
    }
    canvas_element.appendChild(canvas_container);
    socketio.send_to_server("request-list-of-registrations", {filters: __filters});

    // let context_menu = [];
    // if (locations[current_location].type in context_menu_pool) {
    //     context_menu = context_menu_pool[locations[current_location].type];
    //     context_menu = context_menu.concat(context_menu_pool["default"]);
    // } else {
    //     context_menu = context_menu_pool["default"];
    // }
    // context_menu = context_menu.filter(i => !("layout" in i) || i.layout === view_layout_element.value)
    // create_context_menu(context_menu);
    // const extra_filters = locations[current_location].type in extra_filters_pool ? extra_filters_pool[locations[current_location].type] : extra_filters_pool["default"];
    // add_extra_filters(extra_filters);
}

const __location_changed = async (value) => {
    // // Used on students-page when a registration for a student is done
    // __filters.location = value;
    // localStorage.setItem("overview-location-select", value);
    // const registrations = await fetch_get("overview.overview", {...__filters});
    // const initial_data = registrations.map(i => Object.assign(i, {row_action: i.id, DT_RowId: i.id}));
    // datatables_init({config: table_config, initial_data});
    // // base_init({});
    // // each location has it own socketio-room.  This prevents socketio calls to browser that display a different location.
    // socketio.subscribe_to_room(__filters.location);

}

let filter_menu = null;
const filter_menu_items = [
    {
        type: 'select',
        id: 'location',
        label: 'Locaties',
        options: Object.entries(meta.location).sort((a, b) => a[0] - b[0]).map(([k, v]) => ({value: k, label: v.locatie})),
        default: Object.entries(meta.location)[0][0],
        persistent: true,
        cb: __location_changed
    },
    {
        type: 'select',
        id: 'view_layout',
        label: 'Layout',
        options: [{value: "tile", label: "Tegel"}, {value: "list", label: "Lijst"}],
        default: "list",
        persistent: true
    },
    {
        type: 'select',
        id: 'period',
        label: 'Periode',
        options: [{value: "last-week", label: "Laatste week"}, {value: "last-2-months", label: "Laatste 2 maanden"}, {value: "last-4-months", label: "Laatste 4 maanden"}],
        default: "last-week",
        persistent: true
    },
]

const __action_scanner_changed = (id, value) => {
    console.log("scanner changed", value)
    if (value === "on") {
        rfid_serial.connect(data => {
            if (data.type === "state") {
                document.getElementById('scanner').style.backgroundColor = data.value ? "#a7e3a7" : "#deb872";
            }
        });
    } else {
        rfid_serial.disconnect();
    }
}

let action_menu = null;
const action_menu_items = [
    {
        type: 'select',
        id: 'scanner',
        label: 'Scanner',
        options: [{value: "off", label: "Geen"}, {value: "on", label: "Wel"}],
        default: "off",
        persistent: true,
        cb: __action_scanner_changed

    },
]
const __load_registrations = async () => {
    // Used on students-page when a registration for a student is done
    localStorage.setItem("overview-location-select", __filters.location);
    const registrations = await fetch_get("overview.overview", {...__filters});
    const initial_data = registrations.map(i => Object.assign(i, {row_action: i.id, DT_RowId: i.id}));
    datatables_init({config: table_config, initial_data});
    // base_init({});
    // each location has it own socketio-room.  This prevents socketio calls to browser that display a different location.
    socketio.subscribe_to_room(__filters.location);
}

const __filter_changed_cb = async (id, value) => {
    __filters[id] = value;
    console.log(id, value);
    console.log(filter_menu.filters)
    __load_registrations();
}

const __default_actions = () => {
    __action_scanner_changed('scanner', document.getElementById('scanner').value);
    __load_registrations();
}

const table_config = {
    title: "Overview",
    view: "overview",
    width: "50%",
    template: [
        {name: "row_action", data: "row_action", orderable: false, width: "2%", visible: "always"},
        {name: "Tijdstempel", data: "time_in", orderable: true, width: "4%", visible: "yes"},
        {name: "Naam", data: "naam", orderable: true, width: "4%", visible: "yes"},
        {name: "Voornaam", data: "voornaam", orderable: true, width: "4%", visible: "yes"},
        {name: "Klas", data: "klascode", orderable: true, width: "4%", visible: "yes"},
    ]
}

$(document).ready(async function () {
    filter_menu = new FilterMenu(document.querySelector(".filter-menu-placeholder"), filter_menu_items, __filter_changed_cb, "overview");
    __filters = Object.fromEntries(filter_menu.filters.map(f => [f.id, f.value])); // default filter values
    action_menu = new ActionMenu(document.querySelector(".filter-menu-placeholder"), action_menu_items, "overview");
    __default_actions();
    // const registrations = await fetch_get("overview.overview", {...__filters});
    // const initial_data = registrations.map(i => Object.assign(i, {row_action: i.id, DT_RowId: i.id}));
    // datatables_init({config: table_config, initial_data});
    // // base_init({});
    // // each location has it own socketio-room.  This prevents socketio calls to browser that display a different location.
    // socketio.subscribe_to_room(__filters.location);
    // When multiple browsers are displaying the same location, they will be updated simultaneously when e.g. a registration is added
    socketio.subscribe_on_receive("update-list-of-registrations", __socketio_update_list);
    // socketio.subscribe_on_receive("update-items-in-list-of-registrations", __socketio_update_items);
    __create_rules();
    // __request_list_of_registrations_for_current_location();
});

