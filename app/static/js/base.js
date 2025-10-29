import {ButtonMenu} from "./common/button_menu.js";
import {menu} from "./project/menu.js";

export const inject_menu = new_menu => {
    menu = new_menu;
}

export const base_init = ({button_menu_items = []}) => {
    if (suppress_navbar) return;

    const navbar_element = document.querySelector("#navbar");
    let dd_ctr = 0;

    for (const item of menu) {
        if (current_user.level >= item.userlevel) {
            const li = document.createElement("li");
            if ("dropdown" in item) {
                li.classList.add("nav-item", "dropdown");
                const a = document.createElement("a");
                li.appendChild(a)
                a.classList.add("nav-link", "dropdown-toggle");
                a.href = "#";
                a.id = `dd${dd_ctr}`
                a.setAttribute("role", "button");
                a.setAttribute("data-toggle", "dropdown");
                a.setAttribute("aria-haspopup", true);
                a.setAttribute("aria-expanded", true);
                a.innerHTML = item.label; // Use item.label for dropdown title
                const div = document.createElement("div");
                li.appendChild(div)
                div.classList.add("dropdown-menu");
                div.setAttribute("aria-labelledby", `dd${dd_ctr}`)
                for (const sitem_raw of item.dropdown) {
                    if ("divider" in sitem_raw) {
                        const divd = document.createElement("div");
                        divd.classList.add("dropdown-divider");
                        div.appendChild(divd)
                    } else {
                         if (current_user.level >= sitem_raw.userlevel) {
                            const sub_a = document.createElement("a");
                            div.appendChild(sub_a)
                            sub_a.classList.add("dropdown-item");
                            if (typeof sitem_raw.endpoint === "function") {
                                sub_a.onclick = sitem_raw.endpoint;
                            } else {
                                sub_a.href = Flask.url_for(sitem_raw.endpoint);
                            }
                            sub_a.innerHTML = sitem_raw.label;
                        }
                    }
                }
                dd_ctr++;
                // --- End Dropdown Logic ---
            } else {
                // --- Regular menu-item logic ---
                // Check for additional arguments
                let extra_args = {};
                if ("arguments" in item) {
                    for (const arg_item of item.arguments) {
                        extra_args[arg_item.argument] = arg_item.source === "localstorage" ? argument_get(arg_item.argument) : null;
                        if (extra_args[arg_item.argument] === null) extra_args[arg_item.argument] = arg_item.default;
                    }
                }
                const url_path = Flask.url_for(item.endpoint, extra_args);
                li.classList.add("nav-item");
                const a = document.createElement("a");
                a.classList.add("nav-link");
                if (window.location.pathname === url_path.split("?")[0]) {
                    a.classList.add("active");
                }
                a.href = url_path;
                a.innerHTML = item.label;
                li.appendChild(a);
                // --- End Regular menu-item logic ---
            }
            navbar_element.appendChild(li);
        }
    }
    const button_menu = new ButtonMenu(document.querySelector(".button-menu-placeholder"), button_menu_items);
}


// check project tickoff::js/base.js
// A menu item (which is a regular link to a page) can be extended with an extra argument.
// Normally, the extra argument will depend on a filter on that page and is normally stored in localStorage
export const argument_set = (arg, val) => {
    localStorage.setItem(`menu-argument-${arg}`, val);
}

export const argument_get = arg => {
    return localStorage.getItem(`menu-argument-${arg}`);
}