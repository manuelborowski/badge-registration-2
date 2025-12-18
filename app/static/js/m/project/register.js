import {fetch_get, fetch_post, fetch_update} from "../../common/common.js";
import {base_init} from "../base.js";
import {BForms} from "../../common/BForms.js";

const meta = await fetch_get('overview.meta');

class LocationBase {
    item_template = [];
    registration_cache = {};

    async update_line(id) {
        const item = this.registration_cache[id];
        const bform = new BForms(this.item_template);
        const result = await Swal.fire({
            title: `${item.naam} ${item.voornaam}`,
            html: bform.form,
            showCloseButton: true,
            showCancelButton: true,
            focusConfirm: false,
            confirmButtonText: `Ok`,
            confirmButtonAriaLabel: "Ok",
            cancelButtonText: `Annuleer `,
            cancelButtonAriaLabel: "Annuleer",
            didRender: () => {
                bform.populate(item);
            }
        });
        if (result.isConfirmed) {
            const data = bform.get_data();
            Object.assign(item, data);
            data.id = item.id;
            await fetch_update("overview.overview", data);
        }

    }

    render_line (line, extra = "") {
        this.registration_cache[line.id] = line;
        return `<div data-id=${line.id}>${line.time_in.substring(11, 19)}, ${line.klascode}, ${line.naam} ${line.voornaam} ${extra}</div>`
    }
}

class LocationCellphone extends LocationBase {
        render_line (line) {
        return super.render_line(line, `(${line.aantal_items})`);
    }
}

class LocationToilet extends LocationBase {
    render_line (line) {
        return super.render_line(line, `(${line.aantal_items})`);
    }
}

class LocationVerkoop extends LocationBase {}

class LocationSMS extends LocationBase {
    item_template =
        [
            {tag: "link", href: "static/css/form.css", rel: "stylesheet"},
            {
                format: "label-top", rows: [
                    {type: "input", label: "Reden", name: "text1"},
                ],
            },
            {type: "check", label: "Bevestigd", name: "flag2"},
        ]
}

class LocationTimeRegistration extends LocationBase {}

const location_processors = {
    "timeregistration": new LocationTimeRegistration(), "cellphone": new LocationCellphone(), "toilet": new LocationToilet(), "verkoop": new LocationVerkoop(), "sms": new LocationSMS()
}

let location_processor = null;

$(document).ready(async () => {
    const register_type_select = document.getElementById("register-type-select");
    const main = document.getElementById("main");
    const register_list = document.getElementById("register-list");
    const out = document.getElementById("log-out");

    const location_filter_options = Object.entries(meta.locations).filter(i => i[1].access_level <= current_user.level || !i[1].access_level)
        .toSorted((a, b) => a[1].locatie.localeCompare(b[1].locatie))
        .map(([k, v]) => ({value: k, label: v.locatie}));

    const register_type_options = [{label: "Selecteer een type", value: null}, {label: "TEST", value: "test"}].concat(location_filter_options);
    register_type_options.forEach(l => register_type_select.add(new Option(l.label, l.value, false, false)));

    let ndef = null;
    // Select a registration type (or location), load the registrations and open the RFID scanner (if needed)
    register_type_select.addEventListener("change", async (e) => {

        if (["null", "test"].includes(e.target.value)) {
            main.classList.add("register-not-active");
            main.classList.remove("register-active");
        } else {
            main.classList.remove("register-not-active");
            main.classList.add("register-active");
        }

        if (Object.hasOwn(location_processors, meta.locations[register_type_select.value].type)) location_processor = location_processors[meta.locations[register_type_select.value].type];

        register_list.innerHTML = "";
        const registrations = await fetch_get("overview.overview", {location: register_type_select.value, view_layout: "list", period: "today"});
        registrations.forEach(r => register_list.innerHTML += location_processor.render_line(r));
        try {
            if (!ndef) {
                ndef = new NDEFReader();
                await ndef.scan();
                out.value = "Scanner actief";

                ndef.addEventListener("readingerror", () => {
                    out.value("Fout opgetreden");
                });
                ndef.addEventListener("reading", async ({message, serialNumber}) => {
                    out.value = "code-> " + serialNumber.toUpperCase();
                    const data = await fetch_post("registration.registration", {rfid: serialNumber.replaceAll(":", ""), location_key: register_type_select.value});
                    if (data && data.data) {
                        const registration = data.data;
                        register_list.innerHTML = location_processor.render_line(registration) + register_list.innerHTML;
                    }
                });
            }
        } catch (error) {
            out.value = "Fout " + error;
        }
        localStorage.setItem("m-register-location", register_type_select.value);
        timeout_register_type_select();
    });
    // select a registration and open a form to update one or more fields of the registration
    register_list.addEventListener("click", e => {
        location_processor.update_line(e.target.dataset.id);
    });
    base_init();
    const location = localStorage.getItem("m-register-location");
    if (location) {
        register_type_select.value = location;
        register_type_select.dispatchEvent(new Event("change"));
    }
    timeout_register_type_select();
});

// Activate a timeout at page load and when a new location is selected.
// When the page is refreshed before the timeout, the selected location is displayed
// When the page is refreshed after the timeout, a new location needs to be selected.
const LOCATION_SELECT_TIMEOUT = 5 * 60 * 1000;
let timer = null;
const timeout_register_type_select = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
        localStorage.removeItem("m-register-location");
        timer = null;
    }, LOCATION_SELECT_TIMEOUT);
}
