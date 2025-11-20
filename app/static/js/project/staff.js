import {datatable_row_data_from_id, datatables_init, datatable_update_cell} from "../datatables/dt.js";
import {fetch_get, fetch_post, fetch_update} from "../common/common.js";
import {rfid_serial} from "../common/rfidserial.js";

const meta = await fetch_get("overview.meta");
const location_key = "timeregistration";

const __new_registration = (ids) => {
    const staff = datatable_row_data_from_id(ids[0]);
    bootbox.confirm(`Registratie: ${meta.location[location_key].locatie}<br>Voor: ${staff.naam} ${staff.voornaam}`, async result => {
        if (result) {
            const ret = await fetch_post("staff.registration", {location_key, rfid: staff.rfid});
        }
    });
}

let __new_rfid_staff = null;
const __new_rfid = (ids) => {
    __new_rfid_staff = datatable_row_data_from_id(ids[0]);
    bootbox.dialog({
        message: `<span id="new-rfid-dialog">Nieuwe RFID voor: ${__new_rfid_staff.naam} ${__new_rfid_staff.voornaam}
        <br>Huidige RFID: ${__new_rfid_staff.rfid}
        <br>Gelieve de badge te scannen aub</span>`,
        buttons: {ok: {label: "OK", className: "btn-primary", callback: () => __new_rfid_staff = null}, cancel: {label: "Annuleer", className: "btn-warning", callback: () => __new_rfid_staff = null}},
    });
}

const context_menu_items = [
    {type: "item", label: `Nieuwe registratie: ${meta.location[location_key].locatie}`, iconscout: 'plus-circle', cb: ids => __new_registration(ids)},
    {type: "divider"},
    {type: "item", iconscout: "wifi", label: "RFID code aanpassen", cb: ids => __new_rfid(ids)},
]

// called when an RFID is scanned or the state changes.
const __serialrfid_cb = async data => {
    if (__new_rfid_staff) {
        if (data.type === "rfid") {
            const ret = await fetch_update("staff.staff", {rfid: data.rfid, id: __new_rfid_staff.id})
            if (ret) {
                const new_rfid_dialog = document.getElementById("new-rfid-dialog");
                new_rfid_dialog.innerHTML += ` <br>Nieuwe RFID: ${ret.rfid} <br>RFID ok, u kan dit venster sluiten. `;
                datatable_update_cell(__new_rfid_staff.id, "rfid", ret.rfid);
            }
        }
    }
}

const table_config = {
    title: "Personeel",
    view: "staff",
    template: [
        {name: "row_action", data: "row_action", orderable: false, width: "2%", visible: "always"},
        {name: "Naam", data: "naam", orderable: true, width: "4%", visible: "yes"},
        {name: "Voornaam", data: "voornaam", orderable: true, width: "4%", visible: "yes"},
        {name: "Code", data: "code", orderable: true, width: "4%", visible: "yes"},
        {name: "RFID", data: "rfid", orderable: true, width: "4%", visible: "yes"},
        ]
}

$(document).ready(async function () {
    const staffs = await fetch_get("staff.staff")
    const initial_data = staffs.map(i => Object.assign(i, {row_action: i.id, DT_RowId: i.id}));
    const ctx = datatables_init({config: table_config, context_menu_items, initial_data});
    if (localStorage.getItem("action-overview-scanner") === "on") {
        rfid_serial.connect(__serialrfid_cb);
    }
});
