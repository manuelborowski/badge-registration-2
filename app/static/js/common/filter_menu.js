// persistent filter: stored in localStorage and used when page is reloaded
// trigger: [filter-a, filter-b, ...]:  when this filter is changed, all filters (filter-a, ...) get new options
// source: [filter-x, filter-y]: counterpart of "trigger", check values of filter-x, ... to set the correct optionlist for this filter

export class FilterMenu {
    constructor(placeholder, menu, changed_cb, id, reset_button = true) {
        this.id = id;
        this.filter_cache = {};
        this.changed_cb = changed_cb;

        const __add_label = (placeholder, item) => {
            const label = document.createElement("label");
            placeholder.appendChild(label);
            label.classList.add("control-label")
            label.setAttribute("for", item.id);
            label.innerHTML = item.label;
        }

        // Build local store (only persistent filters are stored)
        // Build filter cache, it contains the current filter values (also the non persistent)
        this.store_content = JSON.parse(localStorage.getItem(`Filter-${this.id}`)) || {};
        for (const item of menu) {
            if (!("persistent" in item)) item.persistent = false;
            if (item.persistent) {
                if (!(item.id in this.store_content)) this.store_content[item.id] = "source" in item ? "" : item.default;
                this.filter_cache[item.id] = this.store_content[item.id];
            } else {
                this.filter_cache[item.id] = item.default;
            }
        }
        localStorage.setItem(`Filter-${this.id}`, JSON.stringify(this.store_content));
        this.menu_cache = Object.assign({}, ...menu.map(m => ({[m.id]: m})));

        if (menu.length > 0) {
            // First stage, create the filter-html elements.  Skip adding options when the filter is of the source type.
            for (const item of menu) {
                const form_group = document.createElement("div");
                form_group.classList.add(".filter-form-group");
                if (item.type === "select") {
                    __add_label(form_group, item);
                    const select = document.createElement("select");
                    select.id = item.id;
                    form_group.appendChild(select);
                    select.classList.add("filter-form-control", "table-filter");
                    select.addEventListener("change", e => {
                        this.store_set_item(e.target.id, e.target.value);
                        if ("cb" in this.menu_cache[e.target.id]) this.menu_cache[e.target.id].cb(e.target.value);
                        this.changed_cb(e.target.id, e.target.value);
                    })
                    if (!("source" in item)) {
                        const default_value = this.filter_cache[item.id];
                        for (const o of item.options) select.add(new Option(o.label, o.value, o.value === default_value, o.value === default_value));
                    }
                } else if (item.type === "checkbox") {
                    __add_label(form_group, item);
                    const checkbox = document.createElement("input");
                    form_group.appendChild(checkbox);
                    checkbox.type = "checkbox";
                    checkbox.id = item.id;
                    checkbox.classList.add("filter-form-control", "table-filter");
                    checkbox.addEventListener("click", e => {
                        this.store_set_item(e.target.id, e.target.checked);
                        if ("cb" in this.menu_cache[e.target.id]) this.menu_cache[e.target.id].cb(e.target.checked);
                        this.changed_cb(e.target.id, e.target.checked);
                    });
                } else if (item.type === "button") {
                    const button = document.createElement("a");
                    form_group.appendChild(button);
                    button.type = "button";
                    button.id = item.id;
                    button.classList.add("filter-form-control", "table-filter", "btn", "btn-success");
                    button.innerHTML = item.label;
                    button.addEventListener("click", item.callback);
                }
                placeholder.appendChild(form_group);
            }
            if (reset_button) {
                const button = document.createElement("button");
                placeholder.appendChild(button);
                button.classList.add("btn", "btn-danger");
                button.type = "button";
                button.innerHTML = "Reset";
                button.style.marginRight = "10px";
                button.addEventListener("click", () => {
                    localStorage.removeItem(`Filter-${this.id}`);
                    let url = location.href.split("?")[0]; // remove trailing arguments
                    location.replace(url);
                });
            }
            placeholder.style.display = "flex";

            // second stage, iterate over the filters and set the value of the filter.  This will trigger the "source" filters to add their options.
            // Skip filters of type "source" because the options of these are set when the corresponding source filter has its value set.
            for (const item of menu) {
                if (!("source" in item)) {
                    const default_value = this.filter_cache[item.id];
                    this.store_set_item(item.id, default_value, true);
                }
            }
        }
    }

    get filters() {
        return Object.entries(this.filter_cache).map(k => ({id: k[0], value: k[1]}));
    }

    // init = true: page is being loaded, use values from the store.  Else use default values.
    build_option_list(ids, init = false) {
        for (const id of ids) {
            const item = this.menu_cache[id];
            let options = item.source.options;
            for (const source_id of item.source.id) {
                const source_value = this.filter_cache[source_id];
                options = options[source_value];
            }
            if (options === undefined || options.length === 0) continue
            // Use the stored (cached) value only if it has a valid value (is in the options list), else use the first option as default
            const cache_value = this.filter_cache[id];
            let default_value = options[0].value;
            if (init && options.filter(o => o.value === cache_value).length > 0) default_value = cache_value;
            const filter_element = document.getElementById(id);
            filter_element.innerText = "";
            for (const o of options) filter_element.add(new Option(o.label, o.value, o.value === default_value, o.value === default_value));
            this.store_set_item(item.id, default_value, init);
        }
    }

    store_set_item(id, value, init = false) {
        const item = this.menu_cache[id];
        if (item.persistent)
            this.store_content[id] = value;
        this.filter_cache[id] = value;
        localStorage.setItem(`Filter-${this.id}`, JSON.stringify(this.store_content));
        if ("trigger" in item) this.build_option_list(item.trigger, init);
    }
}