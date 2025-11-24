import {fetch_get, fetch_post, fetch_update} from "./common/common.js";
import {base_init} from "./base.js";
import {BForms} from "./common/BForms.js";
import {settings_template} from "./project/settings_template.js";

const meta = await fetch_get("settings.meta")

const bform = new BForms(settings_template);

const __handle_save = () => {
    document.querySelectorAll(".btn-save").forEach(b => {
        b.addEventListener("click", async e => {
            e.preventDefault();
            const form_data = bform.get_data();
            // Depending on the location of the save button pushed, a single setting is selected or all settings in a section
            const content = e.target.parentElement.closest("div")
            // Consider only the data depending on the save button pushed
            let data = {};
            content.querySelectorAll("[name]").forEach(n => data[n.name] = form_data[n.name]);
            // Process the (variable) list of cron modules (disable or enable)
            const cron_modules = Array.from(content.querySelectorAll(".cron-modules"));
            if (cron_modules.length > 0) data["cron-enable-modules"] = JSON.stringify(Object.fromEntries(cron_modules.map(m => [m.name, form_data[m.name]])));
            await fetch_update("settings.setting", data)
        });
    });
}

const __create_html_page = async () => {
    document.querySelector(".container-form").appendChild(bform.form);
    let cron_modules_template = []
    for (const module of meta.cron_table) cron_modules_template.push({label: module.label, name: module.id, type: "check", class: "cron-modules"})
    bform.add(bform.element("cron-enable-modules"), cron_modules_template)
    bform.populate(meta.cron_enable_modules);

    // Start cron cycle manually
    const cron_start_button = bform.element("button-start-cron-cycle");
    cron_start_button.hidden = true;
    bform.element("display-button-start-cron-cycle").addEventListener("click", e => {
        cron_start_button.hidden = !e.target.checked;
    });
    cron_start_button.addEventListener("click", async e => {
        e.preventDefault();
        await fetch_post("settings.button", {id: e.target.id});
    });

    const settings = await fetch_get("settings.setting");
    if (settings && settings.data) {
        bform.populate(settings.data, meta);
    }

}

$(document).ready(function () {
    __create_html_page();
    __handle_save();
    base_init({});
});

