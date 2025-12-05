import {FilterMenu} from "../common/filter_menu.js";
import {fetch_delete, fetch_get, fetch_post, fetch_update} from "../common/common.js";
import {rfid_serial} from "../common/rfidserial.js";
import {ActionMenu} from "../common/action_menu.js";
import {socketio} from "../common/socketio.js";
import {person_image} from "../../img/base64-person.js";
import {ctx, datatable_clear_checked_boxes, datatable_remove_table, datatable_row_data_from_id, datatable_rows_add, datatable_rows_delete, datatable_update_cell, datatables_init} from "../datatables/dt.js";
import {BForms} from "../common/BForms.js";
import {ContextMenu} from "../common/context_menu.js";
import {base_init} from "../base.js";

// location specific data, parameters and processing is done per location
class LocationBase {
    table_config = {
        title: "Overview", view: "overview",
    }

    table_template = [
        {name: "row_action", data: "row_action", orderable: false, width: "1%", visible: "always"},
        {name: "Tijdstempel", data: "time_in", orderable: true, width: "4%", visible: "yes"},
        {name: "Naam", data: "naam", orderable: true, width: "4%", visible: "yes"},
        {name: "Voornaam", data: "voornaam", orderable: true, width: "4%", visible: "yes"},
        {name: "Klas", data: "klascode", orderable: true, width: "4%", visible: "yes"},
    ]

    context_menu_items = [
        {level: 3, type: "item", label: "Exporteer registraties", iconscout: 'export', cb: () => this.export_registrations()},
        {level: 3, type: "divider"},
        {level: 3, type: "item", label: "Registratie verwijderen", iconscout: "trash-alt", cb: ids => this.delete_registration(ids)},
    ]

    canvas_element = document.getElementById("canvas");
    photo_size_factor = 50;
    current_location = null;
    prev_room = null;

    set location(current_location) {
        this.current_location = current_location;
        this.create_rules_cache();
    }

    export_registrations = async () => {
        const bform = new BForms([{tag: "link", href: "static/css/form.css", rel: "stylesheet"}, {
            format: "vertical-center", rows: [{type: "date", label: "Vanaf datum", name: "from"}, {type: "date", label: "Tot en met datum", name: "till"},]
        }]);
        bootbox.dialog({
            title: "Exporteer registraties", message: bform.form, buttons: {
                confirm: {
                    label: "OK", className: "btn-primary", callback: async () => {
                        const form_data = bform.get_data();
                        window.open(`/registration/export?location=${filters.location}&from=${form_data.from}&till=${form_data.till}`, '_blank');
                    }
                }, cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                    }
                },
            },
        });
    }

    reset_counters = async () => {
        const bform = new BForms([{tag: "link", href: "static/css/form.css", rel: "stylesheet"}, {
            format: "vertical-center", rows: [{type: "date", label: "Tot en met datum", name: "till"},]
        }]);
        bootbox.dialog({
            title: "Tellers op nul zetten", message: bform.form, buttons: {
                confirm: {
                    label: "OK", className: "btn-primary", callback: async () => {
                        const form_data = bform.get_data();
                        await fetch_post("registration.zerocounters", {location: filters.location, date: form_data.till});
                        this.load_registrations();
                    }
                }, cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                    }
                },
            },
        });
    }

    delete_registration = async (ids) => {
        let message = "";
        if (filters.view_layout === "tile") {
            message = `Wilt u de registratie van ${document.querySelector(`figure[data-id="${ids[0]}"]`).dataset.name} verwijderen?`
        } else {
            const registration = datatable_row_data_from_id(ids[0])
            message = `Wilt u de registratie van ${registration.naam} ${registration.voornaam} verwijderen?`
        }
        bootbox.confirm(message, async result => {
            if (result) {
                const ret = await fetch_delete("registration.registration", {id: ids[0]});
                if (ret.data.status) {
                    if (filters.view_layout === "tile") {
                        const tile = document.querySelector(`figure[data-id="${ids[0]}"]`);
                        tile.parentNode.removeChild(tile);
                    } else {
                        datatable_rows_delete(ids);
                    }
                }
            }
        });
    }

    send_message = async (ids) => {
        let message = "";
        if (filters.view_layout === "tile") {
            message = `Wilt u een bericht naar ${document.querySelector(`figure[data-id="${ids[0]}"]`).dataset.name} sturen?`
        } else {
            if (ids.length === 1) {
                const registration = datatable_row_data_from_id(ids[0])
                message = `Wilt u een bericht naar ${registration.naam} ${registration.voornaam} sturen?`
            } else {
                message = `Wilt u bericht naar ${ids.length} studenten sturen?`
            }
        }
        bootbox.confirm(message, async result => {
            if (result) {
                await fetch_post("registration.sendmessage", {ids});
                datatable_clear_checked_boxes();
            }
        });
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

    render_list_view(registrations) {
        const initial_data = this.process_data_list(registrations);
        const config = Object.assign(this.table_config, {template: this.table_template});
        datatables_init({config, initial_data, context_menu_items: this.context_menu_items, callbacks: {created_row: (row, data, dataIndex, cells) => this.process_created_row_callback(data)}});
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
        const timestamp = item.time_in.substring(8, 10) + "/" + item.time_in.substring(5, 7) + " " + item.time_in.substring(11, 17);
        figcaption.innerHTML = "(" + timestamp + ") " + item.klascode + "<br>" + item.naam + " " + item.voornaam;
        figcaption.style.fontSize = (1.5 * this.photo_size_factor / 100).toString() + "rem";
        figcaption.style.fontWeight = "bold";
        figcaption.style.textAlign = "center";
        registration_container.appendChild(image);
        registration_container.appendChild(figcaption);
        registration_container.classList.add("S" + item.leerlingnummer);
        registration_container.dataset.id = item.id;
        registration_container.dataset.name = `${item.naam} ${item.voornaam}`;
        if (prepend) this.canvas_element.prepend(registration_container); else this.canvas_element.appendChild(registration_container);
    }

    render_tile_view(registrations) {
        const get_tile_id = e => [e.target.closest("figure").dataset.id];
        this.canvas_element.innerHTML = "";
        for (const item of registrations) {
            this.render_tile(item);
        }
        ctx.context_menu = new ContextMenu(document.querySelector("#canvas"), this.context_menu_items);
        ctx.context_menu.subscribe_get_ids(get_tile_id);
        base_init({});
    }

    // Each time the page is refreshed, or the location is changed, load and process registrations
    async load_registrations() {
        // Used on students-page when a registration for a student is made
        localStorage.setItem("overview-location-select", filters.location);
        const registrations = await fetch_get("overview.overview", {...filters});
        if (filters.view_layout === "tile") {
            datatable_remove_table();
            this.render_tile_view(registrations);
        } else {
            document.getElementById("canvas").innerHTML = "";
            this.render_list_view(registrations);
        }
        // Depending on the location, the client registers to another room.  When a registration is made for a particular location, only webbrowsers subscribed on that room/location will be notified.
        if (this.prev_room) socketio.unsubscribe_from_room(this.prev_room);
        socketio.subscribe_to_room(filters.location);
        this.prev_room = filters.location;

    }

    // Called by server, via socketio, when a registration is added
    async add_single_registration(type, data) {
        if (filters.view_layout === "tile") {
            this.render_tile(data, true);
        } else {
            data = this.process_data(data);
            if (data.time_diff !== "") datatable_rows_delete([data.id]);
            datatable_rows_add([data]);
        }
    }

    // Called by server, via socketio, when a registration is updated
    async update_single_registration(type, data) {
        if (filters.view_layout === "tile") {
        } else {
            const id = data.id;
            delete data.id;
            const items = Object.entries(data);
            for (const item of items) datatable_update_cell(id, item[0], item[1]);
        }
    }

    // Called by server, via socketio, when a registration is updated
    async update_registrations(type, data) {
        if (filters.view_layout === "tile") {
        } else {
            if (!Array.isArray(data)) data = [data];
            for (const item of data) datatable_update_cell(item.id, item.data, item.value);
        }
    }
}

class LocationCellphone extends LocationBase {
    table_config = Object.assign(this.table_config, {width: "40%"});

    table_template = this.table_template.concat([
        {name: "Bericht", data: "flag1", orderable: false, width: "4%", visible: "yes", display: {template: "%0%", fields: [{field: "flag1", bool: true}]}},
        {name: "Aantal", data: "aantal_items", orderable: false, width: "2%", visible: "yes"},
    ])

    context_menu_items = this.context_menu_items.concat([
        {level: 3, type: "divider"},
        {level: 3, type: "item", label: "Tellers op nul zetten", iconscout: "0-plus", cb: () => this.reset_counters()},
        {level: 3, type: "divider"},
        {level: 3, type: "item", label: "Stuur Smartschool bericht", iconscout: "envelope-send", cb: (ids) => this.send_message(ids)},
    ])
}

class LocationToilet extends LocationBase {
    table_config = Object.assign(this.table_config, {width: "40%"});

    table_template = this.table_template.concat([
        {name: "Aantal", data: "aantal_items", orderable: false, width: "2%", visible: "yes"},
    ])

    context_menu_items = this.context_menu_items.concat([
        {level: 3, type: "divider"}, {level: 3, type: "item", label: "Tellers op nul zetten", iconscout: "0-plus", cb: () => this.reset_counters()},
    ])
}

class LocationVerkoop extends LocationBase {
    table_config = Object.assign(table_config, {width: "40%"});
}

class LocationSMS extends LocationBase {
    table_config = Object.assign(this.table_config, {width: "70%"});

    table_template = this.table_template.concat([
        {name: "SMS", data: "flag1", orderable: false, width: "2%", visible: "yes", display: {template: "%0%", fields: [{field: "flag1", bool: true}]}},
        {name: "Reden te laat", data: "text1", orderable: false, width: "40%", visible: "yes", celledit: {type: "text-confirmkey"}, display: {fields: [{field: "text1"}, {field: "flag2", colors: {true: "#CEEBCC"}}]}},
    ])

    context_menu_items = [
        {level: 3, type: "item", label: "Bevestig reden", iconscout: "check", cb: (ids) => this.set_reason_confirmation(ids, true)},
        {level: 3, type: "item", label: "Verwijder bevestiging", iconscout: "minus", cb: (ids) => this.set_reason_confirmation(ids, false)},
        {level: 3, type: "divider"},
        {level: 3, type: "item", label: "Stuur SMS bericht", iconscout: "envelope-send", cb: (ids) => this.send_message(ids)},
        {level: 3, type: "divider"},
    ].concat(this.context_menu_items);

    async set_reason_confirmation(ids, confirm = true) {
        for (const id of ids) await fetch_update("registration.registration", {id, flag2: confirm});
    }
}

class LocationTimeRegistration extends LocationBase {
    table_template = [
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

    process_data(data) {
        let start = "", stop = "", time_out_diff = "", time_diff = "", time_in_diff = "";
        data = super.process_data(data);
        if (data.text1 !== "") {
            const text1_array = data.text1.split(",");
            if (text1_array.length < 3) [start, time_in_diff] = [...text1_array]; else [start, time_in_diff, stop, time_out_diff, time_diff] = [...text1_array];
        }
        return Object.assign(data, {start, stop, time_in_diff, time_out_diff, time_diff})
    }

    process_data_list(datas) {
        for (const item of datas) {
            this.process_data(item);
        }
        return datas;
    }
}

// this is updated when a filter is changed and can be used throughout the code
let filters = {location: null, view_layout: null, period: null};

// a location processor is an object that contains location specific data/parameters/code
const location_processors = {
    "timeregistration": new LocationTimeRegistration(), "cellphone": new LocationCellphone(), "toilet": new LocationToilet(), "verkoop": new LocationVerkoop(), "sms": new LocationSMS()
}

let location_processor = null;
const set_location_processor = () => {
    location_processor = location_processors[meta.locations[filters.location].type];
    location_processor.location = meta.locations[filters.location];
}

const meta = await fetch_get("overview.meta");

// construct the filter menu in the navigation bar
let filter_menu = null;
const location_filter_options = Object.entries(meta.locations).filter(i => i[1].access_level <= current_user.level || !i[1].access_level)
    .toSorted((a, b) => a[1].locatie.localeCompare(b[1].locatie))
    .map(([k, v]) => ({value: k, label: v.locatie}));
const filter_menu_items = [
    {type: 'select', id: 'location', label: 'Locaties', options: location_filter_options, default: location_filter_options[0].value, persistent: true,},
    {type: 'select', id: 'view_layout', label: 'Layout', options: [{value: "tile", label: "Tegel"}, {value: "list", label: "Lijst"}], default: "list", persistent: true},
    {
        type: 'select', id: 'period', label: 'Periode',
        options: [{value: "today", label: "Vandaag"}, {value: "last-week", label: "Laatste week"}, {value: "last-2-months", label: "Laatste 2 maanden"}, {value: "last-4-months", label: "Laatste 4 maanden"}], default: "last-week", persistent: true
    },
]

// The action menu is located after the filter menu and contains a pull down to enable or disable the RFID scanner
// depending of the state of the scanner, the background color is update to indicate to the user
const action_scanner_changed = (id, value) => {
    if (value === "on") {
        rfid_serial.connect(async data => {
            if (data.type === "state") {
                document.getElementById('scanner').style.backgroundColor = data.value ? "#a7e3a7" : "#deb872";
            } else if (data.type === "rfid") {
                const ret = await fetch_post("registration.registration", {location_key: filters.location, rfid: data.rfid, timestamp: (new Date()).toJSON().substring(0, 19)})
            }
        });
    } else {
        rfid_serial.disconnect();
        document.getElementById('scanner').style.backgroundColor = "white";
    }
}

let action_menu = null;
const action_menu_items = [
    {type: 'select', id: 'scanner', label: 'Scanner', options: [{value: "off", label: "Geen"}, {value: "on", label: "Wel"}], default: "off", persistent: true, cb: action_scanner_changed},
]

// Called each time a filter (location, layout...) has changed
const filter_changed_cb = async (id, value) => {
    filters[id] = value;
    set_location_processor();
    location_processor.load_registrations();
}

// Called once when the page is loaded
const default_actions = () => {
    action_scanner_changed('scanner', document.getElementById('scanner').value);
    set_location_processor();
    location_processor.load_registrations();
}

$(document).ready(async function () {
    filter_menu = new FilterMenu(document.querySelector(".filter-menu-placeholder"), filter_menu_items, filter_changed_cb, "overview");
    filters = Object.fromEntries(filter_menu.filters.map(f => [f.id, f.value])); // default filter values
    action_menu = new ActionMenu(document.querySelector(".filter-menu-placeholder"), action_menu_items, "overview");
    default_actions();
    socketio.subscribe_on_receive("add-registration", (type, data) => location_processor.add_single_registration(type, data));
    socketio.subscribe_on_receive("update-registration", (type, data) => location_processor.update_single_registration(type, data));
    socketio.subscribe_on_receive("update-registrations", (type, data) => location_processor.update_registrations(type, data));
});

