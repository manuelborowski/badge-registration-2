import {navigation_menu} from "./project/navigation_menu.js";

export const inject_menu = new_menu => {
    navigation_menu = new_menu;
}

export const base_init = () => {
    if (suppress_navbar) return;

    const navbar_element = document.querySelector("#navbar");
    navbar_element.innerHTML = "";
    for (const item of navigation_menu) {
        if (current_user.level >= item.userlevel) {
            const li = document.createElement("li");

            // --- Regular menu-item logic ---
            // Check for additional arguments
            const url_path = Flask.url_for(item.endpoint);
            li.classList.add("nav-item");
            const a = document.createElement("a");
            a.classList.add("nav-link");
            a.classList.add(window.location.pathname === url_path.split("?")[0] ? "selected" : "not-selected-not-visible");
            a.href = url_path;
            a.innerHTML = item.label;
            li.appendChild(a);
            navbar_element.appendChild(li);
        }
    }

    document.getElementById("hamburger").addEventListener("click", e => {
        if (e.target.classList.contains("fa-bars")) {
            document.querySelectorAll(".not-selected-not-visible").forEach(a => a.classList.replace("not-selected-not-visible", "not-selected-visible"));
            e.target.classList.replace("fa-bars", "fa-times");
        } else {
            document.querySelectorAll(".not-selected-visible").forEach(a => a.classList.replace("not-selected-visible", "not-selected-not-visible"));
            e.target.classList.replace("fa-times", "fa-bars");

        }
    });

}

