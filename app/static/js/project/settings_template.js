export const settings_template = [
        {
            type: "container", label: "Templates", save: true, default_collapsed: true, rows: [
                {label: "Gebruikers", name: "user-datatables-template", type: "textarea"},
                {label: "Studenten", name: "student-datatables-template", type: "textarea"},
                {label: "Smartschool berichten (HTML)", name: "smartschool-message-templates", type: "textarea"},
                {type: "div", innerHTML: "Smartschool bericht variabelen:<br>%%NAAM%%\n" +
                        "<br>%%VOORNAAM%%\n" +
                        "<br>%%TIJD%%\n" +
                        "<br>%%KLAS%%\n" +
                        "<br>%%AANTAL-OVERTREDINGEN%%"},
            ]
        },
        {
            type: "container", label: "Modules", default_collapsed: true, rows: [
                {
                    type: "container", label: "Algemeen", save: true, default_collapsed: true, rows: [
                        [{label: "Nieuwe gebruikers mogen via Smartschool aanmelden?", name: "generic-new-via-smartschool", type: "check"}],
                        [{label: "Nieuwe gebruikers, standaard niveau", name: "generic-new-via-smartschool-default-level", type: "select"}],
                    ]
                },
                {
                    type: "container", label: "Cron", save: true, default_collapsed: true, rows: [
                        [{label: "Cron template", name: "cron-scheduler-template", type: "input"}],
                        [{label: "Start cron cyclus?", id: "display-button-start-cron-cycle", type: "check", save: false},
                            {label: "Start", id: "button-start-cron-cycle", type: "button", class: "btn btn-success"}],
                        {id: "cron-enable-modules", type: "div"},

                    ]
                },
                {
                    type: "container", label: "Locaties", save: true, default_collapsed: true, rows: [
                        {label: "Locaties (YAML)", name: "location-profiles", type: "textarea"},
                        {label: "Artikelen (YAML)", name: "artikel-profiles", type: "textarea"},
                        {label: "Smartschool account ids (YAML)", name: "ss-internal-numbers", type: "textarea"},
                    ]
                },
                {
                    type: "container", label: "API keys", save: true, default_collapsed: true, rows: [
                        {label: "YAML", name: "api-keys", type: "textarea"},
                    ]
                },
                {
                    type: "container", label: "Logging", save: true, default_collapsed: true, rows: [
                        {label: "YAML", name: "logging-inform-emails", type: "textarea"},
                    ]
                },                {
                    type: "container", label: "Mobiele scanner", save: true, default_collapsed: true, rows: [
                        {label: "Pin", name: "mobile-login-pin", type: "input"},
                    ]
                },
            ]
        }
    ]
