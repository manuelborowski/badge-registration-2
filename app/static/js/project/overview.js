import {FilterMenu} from "../common/filter_menu.js";
import {base_init} from "../base.js";
import {fetch_get, busy_indication_off, busy_indication_on} from "../common/common.js";
import {rfid_serial} from "../common/rfidserial.js";
import {ActionMenu} from "../common/action_menu.js";
import {socketio} from "../common/socketio.js";
import {person_image} from "../../img/base64-person.js";
import {datatable_remove_table, datatable_rows_add, datatables_init} from "../datatables/dt.js";

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

const __row_callback = (data, row) => {
    const rule = __check_rules(data.aantal_items);
    if (rule)
        row.style.backgroundColor = rule.kleur
    else
        row.firstChild.firstChild.disabled = true
}

const table_config = {
    title: "Overview",
    view: "overview",
    width: "50%",
    row_callback: __row_callback,
}
const table_template = {
    student: [
        {name: "row_action", data: "row_action", orderable: false, width: "2%", visible: "always"},
        {name: "Tijdstempel", data: "time_in", orderable: true, width: "4%", visible: "yes"},
        {name: "Naam", data: "naam", orderable: true, width: "4%", visible: "yes"},
        {name: "Voornaam", data: "voornaam", orderable: true, width: "4%", visible: "yes"},
        {name: "Klas", data: "klascode", orderable: true, width: "4%", visible: "yes"},
    ],
    verkoop: [],
    cellphone: [
        {name: "Bericht", data: "flag1", orderable: false, width: "4%", visible: "yes", display: {template: "%0%", fields: [{field: "flag1", bool: true}]}},
        {name: "Aantal", data: "aantal_items", orderable: false, width: "2%", visible: "yes"},
    ],
    toilet: [
        {name: "Aantal", data: "aantal_items", orderable: false, width: "2%", visible: "yes"},
    ]
}

const meta = await fetch_get("overview.meta");


// called by the server when an item (registration) is added
const __socketio_update_list = (type, data) => {
    data = Object.assign(data, {row_action: data.id, DT_RowId: data.id});
    datatable_rows_add([data]);
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


const canvas_element = document.getElementById("canvas");
const __photo_size_factor = 50;
let canvas_container = null;
const __render_tile_view = (registrations) => {
    for (const item of registrations) {
        let registration_container = null;
        registration_container = document.createElement("figure");
        registration_container.style.display = "inline-block";
        registration_container.style.marginRight = "10px";
        registration_container.style.zIndex = "1";
        let src = "data:image/jpeg;base64," + (item.photo !== "" ? item.photo : person_image);
        let image = document.createElement('img');
        image.src = src;
        image.width = (2 * __photo_size_factor).toString();
        let figcaption = document.createElement("figcaption");
        figcaption.innerHTML = "(" + item.time_in.split(" ")[1] + ") " + item.klascode + "<br>" + item.naam + " " + item.voornaam;
        figcaption.style.fontSize = (1.5 * __photo_size_factor / 100).toString() + "rem";
        figcaption.style.fontWeight = "bold";
        figcaption.style.textAlign = "center";
        registration_container.appendChild(image);
        registration_container.appendChild(figcaption);
        registration_container.classList.add("S" + item.leerlingnummer);
        registration_container.dataset.id = item.id;
        registration_container.dataset.name = `${item.naam} ${item.voornaam}`;
        canvas_element.appendChild(registration_container);
    }
}

const __render_list_view = (registrations) => {
    const location = meta.location[__filters.location];
    const initial_data = registrations.map(i => Object.assign(i, {row_action: i.id, DT_RowId: i.id}));
    let config = {}
    if (location.table && location.table === "staff") {} else {
        const template = table_template.student.concat(table_template[location.type]);
        config = Object.assign(table_config, {template})
    }
    datatables_init({config, initial_data});
}

const __load_registrations = async () => {
    // Used on students-page when a registration for a student is made
    localStorage.setItem("overview-location-select", __filters.location);
    const registrations = await fetch_get("overview.overview", {...__filters});
    if (__filters.view_layout === "tile") {
        datatable_remove_table();
        __render_tile_view(registrations);
    } else {
        canvas_element.innerHTML = "";
        __render_list_view(registrations);
    }
    // each location has it own socketio-room.  This prevents socketio calls to browsers that display a different location.
    socketio.subscribe_to_room(__filters.location);
}

// Depending on the location, the client registers to another room
let __prev_room = null;
const __socketio_subscribe_to_room = () => {
    if (__prev_room) socketio.unsubscribe_from_room(__prev_room);
    socketio.subscribe_to_room(__filters.location);
    __prev_room = __filters.location;
}

const __filter_changed_cb = async (id, value) => {
    __filters[id] = value;
    __create_rules();
    __load_registrations();
    __socketio_subscribe_to_room();
}

const __default_actions = () => {
    __action_scanner_changed('scanner', document.getElementById('scanner').value);
    __create_rules();
    __load_registrations();
    __socketio_subscribe_to_room();
}

$(document).ready(async function () {
    filter_menu = new FilterMenu(document.querySelector(".filter-menu-placeholder"), filter_menu_items, __filter_changed_cb, "overview");
    __filters = Object.fromEntries(filter_menu.filters.map(f => [f.id, f.value])); // default filter values
    action_menu = new ActionMenu(document.querySelector(".filter-menu-placeholder"), action_menu_items, "overview");
    __default_actions();
    socketio.subscribe_on_receive("add-registration", __render_tile_view);
});

