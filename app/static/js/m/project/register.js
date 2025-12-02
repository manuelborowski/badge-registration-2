import {fetch_get, fetch_post} from "../../common/common.js";
import {base_init} from "../base.js";

$(document).ready(async () => {
    const register_type_select = document.getElementById("register-type-select");
    const main = document.getElementById("main");
    const register_list = document.getElementById("register-list");
    const out = document.getElementById("log-out");
    const clear_list_button = document.getElementById("clear-list-btn");

    const meta = await fetch_get('registration.meta');

    const register_type_options = [{label: "Selecteer een type", value: null}, {label: "TEST", value: "test"}].concat(meta.locations);
    register_type_options.forEach(l => register_type_select.add(new Option(l.label, l.value, false, false)));

    let ndef = null;

    const registration_cache = JSON.parse(localStorage.getItem("registrations")) || {};

    register_type_select.addEventListener("change", async (e) => {
        if (["null", "test"].includes(e.target.value)) {
            main.classList.add("register-not-active");
            main.classList.remove("register-active");
        } else {
            main.classList.remove("register-not-active");
            main.classList.add("register-active");
        }
        if (e.target.value in registration_cache) {
            register_list.innerHTML = registration_cache[e.target.value];
        } else {
            register_list.innerHTML = "";
        }
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
                        register_list.innerHTML = `${registration.time_in.substring(11, 19)}, ${registration.klascode}, ${registration.naam} ${registration.voornaam}<br>` + register_list.innerHTML;
                        registration_cache[e.target.value] = register_list.innerHTML;
                        localStorage.setItem("registrations", JSON.stringify(registration_cache));
                    }
                });
            }
        } catch (error) {
            out.value = "Fout " + error;
        }
    });

    clear_list_button.addEventListener("click", () => {
        bootbox.confirm("Bent u zeker?", result => {
            if (result) {
                if (register_type_select.value in registration_cache) {
                    delete registration_cache[register_type_select.value];
                    localStorage.setItem("registrations", JSON.stringify(registration_cache));
                }
                register_list.innerHTML = "";
            }
        });
    });
    base_init();
});
