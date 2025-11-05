import {datatable_row_data_from_id, datatables_init} from "../datatables/dt.js";
import {fetch_get, fetch_post} from "../common/common.js";

const meta = await fetch_get("overview.meta");
const location_key = localStorage.getItem("overview-location-select");

const __new_registration = (ids) => {
    const student = datatable_row_data_from_id(ids[0]);
    bootbox.confirm(`Registratie: ${meta.location[location_key].locatie}<br>Voor: ${student.naam} ${student.voornaam}`, async result => {
        if (result) {
            const ret = await fetch_post("student.registration", {location_key, leerlingnummer: student.leerlingnummer});
        }
    });
}

const context_menu_items = [
    {type: "item", label: `Nieuwe registratie: ${meta.location[location_key].locatie}`, iconscout: 'plus-circle', cb: ids => __new_registration(ids)},
]

$(document).ready(function () {
    const ctx = datatables_init({context_menu_items});
});
