import {datatable_row_data_from_id, datatables_init} from "../datatables/dt.js";
import {fetch_get, fetch_post} from "../common/common.js";

const meta = await fetch_get("overview.meta");
const location_key = localStorage.getItem("overview-location-select");

const __new_registration = (ids) => {
    const staff = datatable_row_data_from_id(ids[0]);
    bootbox.confirm(`Registratie: ${meta.location[location_key].locatie}<br>Voor: ${staff.naam} ${staff.voornaam}`, async result => {
        if (result) {
            const ret = await fetch_post("staff.registration", {location_key, rfid: staff.rfid});
        }
    });
}

const context_menu_items = [
    {type: "item", label: `Nieuwe registratie: ${meta.location[location_key].locatie}`, iconscout: 'plus-circle', cb: ids => __new_registration(ids)},
]

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
});
