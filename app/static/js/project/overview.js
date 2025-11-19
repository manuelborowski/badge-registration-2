import {FilterMenu} from "../common/filter_menu.js";
import {base_init} from "../base.js";
import {fetch_get, busy_indication_off, busy_indication_on} from "../common/common.js";
import {rfid_serial} from "../common/rfidserial.js";
import {ActionMenu} from "../common/action_menu.js";
import {socketio} from "../common/socketio.js";
import {person_image} from "../../img/base64-person.js";
import {datatable_column2index, datatable_remove_table, datatable_rows_add, datatable_rows_delete, datatables_init} from "../datatables/dt.js";

// location specific data, parameters and processing is done per location
class LocationBase {
    table_config = {
        title: "Overview",
        view: "overview",
    }

    base_table_template = {
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

    canvas_element = document.getElementById("canvas");
    photo_size_factor = 50;
    current_location = null;

    set location(current_location) {
        this.current_location = current_location;
        this.create_rules_cache();
    }

    // rules (per location) define how a registration is processed; do nothing, add color, add tickbox...
    // can be changed via the settings page
    rules_cache = null;

    create_rules_cache() {
        this.rules_cache = {"=": [], "<": [], ">": []}
        if ("regel" in this.current_location) this.current_location.regel.forEach(r => this.rules_cache[r.operator].push(r));
    }

    check_rules(data) {
        if (this.current_location.regel === undefined) return;
        if (this.rules_cache["="].length) for (const rule of this.rules_cache["="]) if (data.aantal_items === rule.limiet) {
            data.row_color = rule.kleur;
            return
        }
        if (this.rules_cache["<"].length) for (const rule of this.rules_cache["<"]) if (data.aantal_items < rule.limiet) {
            data.row_color = rule.kleur;
            return
        }
        if (this.rules_cache[">"].length) for (const rule of this.rules_cache[">"]) if (data.aantal_items > rule.limiet) {
            data.row_color = rule.kleur;
            return
        }
        data.disable_selectbox = true;
    }

    process_data(data) {
        return Object.assign(data, {row_action: data.id, DT_RowId: data.id});
    }

    process_data_list(datas) {
        for (const item of datas) {
            this.process_data(item);
        }
        return datas;
    }

    process_created_row_callback(data, row) {
        this.check_rules(data);
    }

    render_list_view(registrations, extra_template) {
        const initial_data = this.process_data_list(registrations);
        const config = Object.assign(this.table_config, {template: this.base_table_template.student.concat(extra_template)});
        datatables_init({config, initial_data, callbacks: {created_row: (row, data, dataIndex, cells) => this.process_created_row_callback(data)}});
    }

    render_tile(item, prepend = false) {
        let registration_container = null;
        registration_container = document.createElement("figure");
        registration_container.style.display = "inline-block";
        registration_container.style.marginRight = "10px";
        registration_container.style.zIndex = "1";
        let src = "data:image/jpeg;base64," + (item.photo !== "" ? item.photo : person_image);
        let image = document.createElement('img');
        image.src = src;
        image.width = (2 * this.photo_size_factor).toString();
        let figcaption = document.createElement("figcaption");
        figcaption.innerHTML = "(" + item.time_in.split(" ")[1] + ") " + item.klascode + "<br>" + item.naam + " " + item.voornaam;
        figcaption.style.fontSize = (1.5 * this.photo_size_factor / 100).toString() + "rem";
        figcaption.style.fontWeight = "bold";
        figcaption.style.textAlign = "center";
        registration_container.appendChild(image);
        registration_container.appendChild(figcaption);
        registration_container.classList.add("S" + item.leerlingnummer);
        registration_container.dataset.id = item.id;
        registration_container.dataset.name = `${item.naam} ${item.voornaam}`;
        if (prepend)
            this.canvas_element.prepend(registration_container);
        else
            this.canvas_element.appendChild(registration_container);
    }

    render_tile_view(registrations) {
        this.canvas_element.innerHTML = "";
        for (const item of registrations) {
            this.render_tile(item);
        }
    }

}

class LocationCellphone extends LocationBase {
    table_template = [
        {name: "Bericht", data: "flag1", orderable: false, width: "4%", visible: "yes", display: {template: "%0%", fields: [{field: "flag1", bool: true}]}},
        {name: "Aantal", data: "aantal_items", orderable: false, width: "2%", visible: "yes"},
    ]

    render_list_view(registrations) {
        super.render_list_view(registrations, this.table_template);
    }
}

class LocationToilet extends LocationBase {
    table_template = [
        {name: "Aantal", data: "aantal_items", orderable: false, width: "2%", visible: "yes"},
    ]

    render_list_view(registrations) {
        super.render_list_view(registrations, this.table_template);
    }
}

class LocationVerkoop extends LocationBase {
    table_template = []

    render_list_view(registrations) {
        super.render_list_view(registrations, this.table_template);
    }
}

class LocationSMS extends LocationBase {
    table_template = []

    render_list_view(registrations) {
        super.render_list_view(registrations, this.table_template);
    }
}

class LocationTimeRegistration extends LocationBase {
    table_template = {
        staff: [
            {name: "row_action", data: "row_action", orderable: false, width: "2%", visible: "always"},
            {name: "Naam", data: "naam", orderable: true, width: "4%", visible: "yes"},
            {name: "Voornaam", data: "voornaam", orderable: true, width: "4%", visible: "yes"},
            {name: "code", data: "code", orderable: true, width: "4%", visible: "yes"},
            {name: "Tijd in", data: "time_in", orderable: true, width: "8%", visible: "yes"},
            {name: "Startuur", data: "start", orderable: true, width: "4%", visible: "yes"},
            {name: "Verschil", data: "time_in_diff", orderable: true, width: "4%", visible: "yes"},
            {name: "Tijd uit", data: "time_out", orderable: true, width: "8%", visible: "yes"},
            {name: "Einduur", data: "stop", orderable: true, width: "4%", visible: "yes"},
            {name: "Verschil", data: "time_out_diff", orderable: true, width: "4%", visible: "yes"},
            {name: "Dagverschil", data: "time_diff", orderable: true, width: "4%", visible: "yes"},
            {name: "Opmerking", data: "info", orderable: true, width: "50%", visible: "yes", celledit: {type: "text-confirmkey"}},
        ]
    }

    process_data(data) {
        let start = "", stop = "", time_out_diff = "", time_diff = "", time_in_diff = "";
        data = super.process_data(data);
        if (data.text1 !== "") {
            const text1_array = data.text1.split(",");
            if (text1_array.length < 3)
                [start, time_in_diff] = [...text1_array];
            else
                [start, time_in_diff, stop, time_out_diff, time_diff] = [...text1_array];
        }
        return Object.assign(data, {start, stop, time_in_diff, time_out_diff, time_diff})
    }

    process_data_list(datas) {
        for (const item of datas) {
            this.process_data(item);
        }
        return datas;
    }

    render_list_view(registrations) {
        const initial_data = this.process_data_list(registrations);
        const config = Object.assign(this.table_config, {template: this.table_template.staff})
        datatables_init({config, initial_data, callbacks: {created_row: (row, data, dataIndex, cells) => this.process_created_row_callback(data)}});
    }

}

// this is updated when a filter is changed and can be used throughout the code
let filters = {location: null, view_layout: null, period: null};

// a location processor is an object that contains location specific data/parameters/code
const location_processors = {
    "timeregistration": new LocationTimeRegistration(),
    "cellphone": new LocationCellphone(),
    "toilet": new LocationToilet(),
    "verkoop": new LocationVerkoop(),
    "sms": new LocationSMS()
}

let location_processor = null;
const set_location_processor = () => {
    location_processor = location_processors[meta.location[filters.location].type];
    location_processor.location = meta.location[filters.location];
}

const meta = await fetch_get("overview.meta");

// construct the filter menu in the navigation bar
let filter_menu = null;
const location_filter_options = Object.entries(meta.location).filter(i => i[1].access_level <= current_user.level || !i[1].access_level)
    .toSorted((a, b) => a[1].locatie.localeCompare(b[1].locatie))
    .map(([k, v]) => ({value: k, label: v.locatie}));
const filter_menu_items = [
    {
        type: 'select',
        id: 'location',
        label: 'Locaties',
        options: location_filter_options,
        default: location_filter_options[0].value,
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

// The action menu is located after the filter menu and contains a pull down to enable or disable the RFID scanner
// depending of the state of the scanner, the background color is update to indicate to the user
const action_scanner_changed = (id, value) => {
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
        cb: action_scanner_changed

    },
]

// Depending on the location, the client registers to another room.  When a registration is made for a particular location, only webbrowsers subscribed on that room/location will be notified.
let prev_room = null;
const subscribe_to_room = () => {
    if (prev_room) socketio.unsubscribe_from_room(prev_room);
    socketio.subscribe_to_room(filters.location);
    prev_room = filters.location;
}

// Each time the page is refreshed, or the location is changed, load and process registrations
const load_registrations = async () => {
    // Used on students-page when a registration for a student is made
    localStorage.setItem("overview-location-select", filters.location);
    const registrations = await fetch_get("overview.overview", {...filters});
    if (filters.view_layout === "tile") {
        datatable_remove_table();
        location_processor.render_tile_view(registrations);
    } else {
        document.getElementById("canvas").innerHTML = "";
        location_processor.render_list_view(registrations);
    }
    // each location has it own socketio-room.  This prevents socketio calls to browsers that display a different location.
    subscribe_to_room();
}

// Called by server, via socketio, when a registration is added
const add_single_registration = async (type, data) => {
    if (filters.view_layout === "tile") {
        location_processor.render_tile(data, true);
    } else {
        data = location_processor.process_data(data);
        if (data.time_diff !== "") datatable_rows_delete([data.id]);
        datatable_rows_add([data]);
    }
}

// Called each time a filter (location, layout...) has changed
const filter_changed_cb = async (id, value) => {
    filters[id] = value;
    set_location_processor();
    load_registrations();
    subscribe_to_room();
}

// Called once when the page is loaded
const default_actions = () => {
    action_scanner_changed('scanner', document.getElementById('scanner').value);
    set_location_processor();
    load_registrations();
    subscribe_to_room();
}

$(document).ready(async function () {
    filter_menu = new FilterMenu(document.querySelector(".filter-menu-placeholder"), filter_menu_items, filter_changed_cb, "overview");
    filters = Object.fromEntries(filter_menu.filters.map(f => [f.id, f.value])); // default filter values
    action_menu = new ActionMenu(document.querySelector(".filter-menu-placeholder"), action_menu_items, "overview");
    default_actions();
    socketio.subscribe_on_receive("add-registration", add_single_registration);
});

