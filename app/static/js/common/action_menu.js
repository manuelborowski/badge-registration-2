export class ActionMenu {
    constructor(placeholder, menu, id="") {
        this.menu = menu;
        this.id = id;
        this.filters = [];
        if (menu.length > 0) {
            for (const item of menu) {
                let element = null;
                if (item.type === "button") {
                    element = document.createElement("button");
                    element.classList.add("btn");
                    element.type = "button";
                    element.innerHTML = item.label;
                    element.addEventListener("click", item.cb);
                    element.id = item.id;
                } else if (item.type === "text") {
                    element = document.createElement("label");
                    element.innerHTML = item.label;
                    const input = document.createElement("input");
                    element.appendChild(input);
                    input.type = "text";
                    input.disabled = true;
                    input.id = item.id;
                    if ("width" in item) input.style.width = item.width;
                } else if (item.type === "label") {
                    element = document.createElement("label");
                    element.innerHTML = item.label;
                    element.id = item.id;
                } else if (item.type === "select") {
                    element = document.createElement("div");
                    element.classList.add(".filter-form-group");
                    const label = document.createElement("label");
                    element.appendChild(label);
                    label.classList.add("control-label")
                    label.setAttribute("for", item.id);
                    label.innerHTML = item.label;
                    const select = document.createElement("select");
                    select.classList.add("filter-form-control", "table-filter");
                    const default_value = localStorage.getItem(`action-${id}-${item.id}`) || item.default;
                    for (const o of item.options) select.add(new Option(o.label, o.value, o.value === default_value, o.value === default_value));
                    select.addEventListener("change", e => {
                        if (item.persistent) localStorage.setItem(`action-${id}-${item.id}`, e.target.value);
                        if (item.cb) item.cb(item.id, e.target.value);
                    });
                    select.id = item.id;
                    element.appendChild(select);
                }
                if (element) {
                    placeholder.appendChild(element);
                    if ("align" in item) element.classList.add(`align-${item.align}`);
                    if ("class" in item) element.classList.add(...item.class);
                    element.style.marginRight = "10px";
                }
            }
        }
    }
}