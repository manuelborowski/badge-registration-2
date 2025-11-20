import {datatable_reload_table, datatable_row_data_from_id, datatable_update_cell, datatables_init} from "../datatables/dt.js";
import {fetch_get, fetch_post, fetch_update} from "../common/common.js";
import {rfid_serial} from "../common/rfidserial.js";
import {BForms} from "../common/BForms.js";

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

let __new_rfid_student = null;
const __new_rfid = (ids) => {
    __new_rfid_student = datatable_row_data_from_id(ids[0]);
    bootbox.dialog({
        message: `<span id="new-rfid-dialog">Nieuwe RFID voor: ${__new_rfid_student.naam} ${__new_rfid_student.voornaam}
        <br>Huidige RFID: ${__new_rfid_student.rfid}
        <br>Gelieve de badge te scannen aub</span>`,
        buttons: {ok: {label: "OK", className: "btn-primary", callback: () => __new_rfid_student = null}, cancel: {label: "Annuleer", className: "btn-warning", callback: () => __new_rfid_student = null}},
    });
}

const __export_balances_cb = async () => {
    const bform = new BForms(
        [
            {tag: "link", href: "static/css/form.css", rel: "stylesheet"},
            {
                format: "vertical-center", rows: [
                    {type: "date", label: "Vanaf datum", name: "from"},
                    {type: "date", label: "Tot en met datum", name: "till"},
                ]
            }
        ]
    );
    bootbox.dialog({
        title: "Exporteer leerlingrekeningen",
        message: bform.form,
        buttons: {
            confirm: {
                label: "OK",
                className: "btn-primary",
                callback: async () => {
                    const form_data = bform.get_data();
                    for (const [key, location] of Object.entries(meta.location)) {
                        if (location.type === "verkoop") {
                            window.open(`/student/balance/${key}/${form_data.from}/${form_data.till}`, '_blank');
                        }
                    }
                }
            },
            cancel: {
                label: "Annuleer", className: "btn-secondary", callback: async () => {
                }
            },
        },
        onShown: async () => {
        },
    });
}

const papercut_items = ["sui", "sul", "sum"]

const __import_papercut_data_cb = async () => {
    const form = document.createElement("form")
    const input = document.createElement('input');
    form.appendChild(input)
    input.type = 'file';
    input.name = "papercut_file";
    input.multiple = true;
    input.accept = ".xlsx,.xls, .csv"
    input.onchange = async e => {
        const form_data = new FormData(form);
        const status = await fetch_post('student.papercut', form_data, true);
        if (status.data) {
            papercut_items.forEach(item => window.open(`/student/papercut/export/${item}`, '_blank'))
        }
    }
    input.click();
}

const context_menu_items = [
    {type: "item", label: `Nieuwe registratie: ${meta.location[location_key].locatie}`, iconscout: 'plus-circle', cb: ids => __new_registration(ids)},
    {type: "divider"},
    {type: "item", iconscout: "wifi", label: "RFID code aanpassen", cb: ids => __new_rfid(ids)},
    {type: "divider"},
    {type: "item", iconscout: "export", label: "Exporteer leerling rekeningen", cb: __export_balances_cb},
    {type: "item", iconscout: "print", label: "Exporteer leerling printer rekeningen", cb: __import_papercut_data_cb},
]

// called when an RFID is scanned or the state changes.
const __serialrfid_cb = async data => {
    if (__new_rfid_student) {
        if (data.type === "rfid") {
            const ret = await fetch_update("student.student", {rfid: data.rfid, id: __new_rfid_student.id})
            if (ret) {
                const new_rfid_dialog = document.getElementById("new-rfid-dialog");
                new_rfid_dialog.innerHTML += ` <br>Nieuwe RFID: ${ret.rfid} <br>RFID ok, u kan dit venster sluiten. `;
                datatable_update_cell(__new_rfid_student.id, "rfid", ret.rfid);
            }
        }
    }
}

$(document).ready(function () {
    const ctx = datatables_init({context_menu_items});
    if (localStorage.getItem("action-overview-scanner") === "on") {
        rfid_serial.connect(__serialrfid_cb);
    }
});
