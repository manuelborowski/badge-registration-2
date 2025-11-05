import {datatables_init, datatable_reload_table} from "../datatables/dt.js";
import {fetch_post, fetch_get, fetch_update, fetch_delete} from "../common/common.js";
import {BForms} from "../common/BForms.js";

const meta = await fetch_get("user.meta");

const template =
    [
        {tag: "link", href: "static/css/form.css", rel: "stylesheet"},
        {
            format: "vertical-center", rows: [
                {type: "input", label: "Gebruikersnaam", name: "username"},
                {type: "input", label: "Achternaam", name: "last_name"},
                {type: "input", label: "Voornaam", name: "first_name"},
                {type: "input", label: "Email", name: "email"},
                {type: "select", label: "Niveau", name: "level", typecast: "integer"},
                {type: "select", label: "Type", name: "user_type"},
                {type: "check", label: "Nieuw wachtwoord?", id: "new-password-check"},
                {type: "input", label: "Paswoord", id: "new-password", name: "password"},
                {type: "input", label: "Bevestig paswoord", id: "new-password-confirm"},
            ]
        }
    ]

const __user_add_or_update = async (ids, add = true) => {
    const users = add ? null : await fetch_get("user.user", {filters: `id$=$${ids[0]}`})
    const bform = new BForms(template);

    const title = add ? "Nieuwe gebruiker" : "Gebruiker aanpassen";
    bootbox.dialog({
        title,
        message: bform.form,
        buttons: {
            confirm: {
                label: "Bewaar",
                className: "btn-primary",
                callback: async () => {
                    const form_data = bform.get_data();
                    if (add)
                        await fetch_post("user.user", form_data);
                    else
                        await fetch_update("user.user", form_data);
                    datatable_reload_table();

                }
            },
            cancel: {
                label: "Annuleer", className: "btn-secondary", callback: async () => {
                }
            },
        },
        onShown: async () => {
            if (add)
                bform.populate({level: meta.default.level, user_type: meta.default.user_type}, meta);
            else
                bform.populate(users[0], meta);
            bform.element("new-password-check").addEventListener("click", e => {
                bform.element("new-password").closest("div").hidden = !e.target.checked;
                bform.element("new-password-confirm").closest("div").hidden = !e.target.checked;
            })
            bform.element("new-password-check").dispatchEvent(new Event("click"));
        },
    });
}

const __users_delete = async (ids) => {
    bootbox.confirm("Wilt u deze gebruiker(s) verwijderen?", async result => {
        if (result) {
            await fetch_delete("user.user", {ids})
            datatable_reload_table();
        }
    });
}

const context_menu_items = [
    {type: "item", label: 'Nieuwe gebruiker', iconscout: 'plus-circle', cb: ids => __user_add_or_update(ids, true)},
    {type: "item", label: 'Gebruiker aanpassen', iconscout: 'pen', cb: ids => __user_add_or_update(ids, false)},
    {type: "item", label: 'Gebruiker(s) verwijderen', iconscout: 'trash-alt', cb: __users_delete},
]

const filter_menu_items = [
    {
        type: 'select',
        id: 'user-type',
        label: 'Type',
        options: [{value: "all", label: "Alles"}, {value: "local", label: "local"}, {value: "oauth", label: "oauth"}],
        default: 'all',
        persistent: true
    },
    {
        type: 'select',
        id: 'user-level',
        label: 'Niveau',
        options: [{value: "all", label: "Alles"}, {value: "1", label: "gebruiker"}, {value: "3", label: "secretariaat"}, {value: "4", label: "secretariaat+"},
            {value: "5", label: "admin"}],
        default: 'all',
        persistent: false
    },
]

$(document).ready(function () {
    datatables_init({context_menu_items, filter_menu_items});
});
