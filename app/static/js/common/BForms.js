// List of html elements.  Elements can be located in containers (and sub-containers) to collected similar elements together.
// Containers can be collapsible to minimize the clutter and maximize the overview on a page.
// const template =
//     [
// Insert a literal html element
// tag: type of the html element to be inserted
// href: href attribute
// rel: rel attribute
//        {tag: "link", href: "static/css/form.css", rel: "stylesheet"},

// Container, contains a header with the name and can be collapsible
// save:  If true, a save button is added at the top of the container
// default_collapsed:  If present, the container is collapsible.  If present and true, the container is default closed
// rows: sub containers of elements
//         {
//             type: "container", label: "Templates", save: true, default_collapsed: true, rows: [
//
// Single row with one element
// name: the name attribute of the element
// save: if present and true, a save button is added in front of the element
// type: textarea, check, select, input
//                 {label: "Gebruikers", name: "user-datatables-template", type: "textarea", save: true},
// Single row with two elements, i.e. it is a list
//                [{label: "Start cron cyclus?", id: "display-button-start-cron-cycle", type: "check", save: false},
//                             {label: "Start", id: "button-start-cron-cycle", type: "button", save: false}],
// Placeholder div, to insert arbitrary html code
// id: the id attribute
// type: div
//                         {id: "cron-enable-modules", type: "div"},
// Format all elements inside the section
// format: type of formatting.  "vertical-center": all labels are right aligned agains a vertical line, all elements are left aligned against the vertical line
// rows: list of elements that need to be formatted
//         {
//             format: "vertical-center", rows: [
//                 {type: "input", label: "Gebruikersnaam", name: "username"},
//             ]
//         }


export class BForms {
    id2element = {}
    typecasts = []

    constructor(template) {
        this.form = document.createElement("form");
        this.add(this.form, template)
    }

    // add a template to the form
    // parent: html element to which the rendered template is attachted to
    // template: structure defining the html elemeents of the form
    add = (parent, template) => {
        let container_level = 0;
        let format = null;

        const __add_tag_attributes = (element, tag) => {
            if (tag) {
                if ("name" in element) tag.name = element.name;
                if ("id" in element) tag.id = element.id;
                if ("class" in element) tag.classList.add(...element.class.split(" "));
                if ("href" in element) tag.href = element.href;
                if ("src" in element) tag.src = element.src;
                if ("rel" in element) tag.rel = element.rel;
                if ("innerHTML" in element) tag.innerHTML = element.innerHTML;
                if ("style" in element) tag.style = element.style;
                if ("tagtype" in element) tag.type = element.tagtype;
                if ("hidden" in element) {
                    if ("type" in element)
                        tag.parentElement.closest(".form-row").hidden = element.hidden;
                    else
                        tag.hidden = element.hidden;
                }
                if ("attribute" in element) {
                    for (const [k, v] of Object.entries(element.attribute)) tag[k] = v;
                }
            }
        }

        const __iterate_template = (component, parent) => {
            if ("tag" in component) { // Create an HTML tag
                const tag = document.createElement(component.tag);
                __add_tag_attributes(component, tag);
                parent.appendChild(tag);
                if ("id" in component) this.id2element[component.id] = {element: tag, type: "element"};
            } else if (component.type === "container") { // This is a container component
                container_level++;
                if ("format" in component) format = component.format;
                const button = document.createElement("button");
                parent.appendChild(button);
                button.type = "button";
                button.innerText = component.label;
                button.classList.add("form-container", `form-container-${container_level}`);
                const content = document.createElement("div");
                parent.appendChild(content);
                content.classList.add("content");
                if ("default_collapsed" in component) {
                    button.classList.add("form-container-collapsible");
                    if (component.default_collapsed) content.style.display = "none";
                }
                if ("save" in component && component.save) {
                    const save_button = document.createElement("button");
                    save_button.classList.add("btn", "btn-success", "btn-save")
                    save_button.innerText = "Bewaar sectie";
                    save_button.style.margin = "10px";
                    content.appendChild(save_button);
                }
                for (const row of component.rows) __iterate_template(row, content);
                format = null;
            } else if ("format" in component) {
                format = component.format;
                for (const row of component.rows) __iterate_template(row, parent);
                format = null;
            } else if ("group" in component) {
                const tag = document.createElement("div");
                parent.append(tag);
                tag.id = component.group;
                this.id2element[component.group] = {element: tag, type: "group"}
                __add_tag_attributes(component, tag)
                for (const row of component.rows) __iterate_template(row, tag);
            } else { // This is a row in the form
                const form_row = document.createElement("div");
                parent.appendChild(form_row);
                form_row.classList.add("form-row");
                if (!Array.isArray(component)) component = [component];
                for (const element of component) { // multiple elements on a single row
                    const form_element = document.createElement("div");
                    form_row.appendChild(form_element);
                    form_element.classList.add("form-element");
                    let tag = null;
                    if (element.type === "div") {
                        tag = document.createElement("div");
                        form_element.appendChild(tag);
                    } else if (element.type === "button") {
                        tag = document.createElement("button");
                        tag.innerText = element.label;
                        form_element.appendChild(tag);
                    } else {
                        const text = document.createTextNode(element.label);
                        const span = document.createElement("span");
                        if ("save" in element && element.save) {
                            const save_button = document.createElement("button");
                            save_button.classList.add("btn", "btn-success", "btn-save")
                            save_button.innerText = "Bewaar";
                            save_button.style.marginRight = "10px";
                            span.appendChild(save_button);
                        }
                        span.appendChild(text);
                        const label = document.createElement("label");
                        form_element.appendChild(label);
                        if (element.type === "textarea") {
                            tag = document.createElement("textarea");
                            tag.rows = "10";
                            tag.cols = "150";
                            label.classList.add("top");
                        } else if (element.type === "check") {
                            tag = document.createElement("input");
                            tag.type = "checkbox"
                        } else if (element.type === "select") {
                            tag = document.createElement("select");
                        } else if (element.type === "input") {
                            tag = document.createElement("input");
                        } else if (element.type === "date") {
                            tag = document.createElement("input");
                            tag.type = "date"
                        }
                        if (tag) {
                            label.appendChild(span);
                            label.appendChild(tag);
                            if (format) {
                                if (format === "vertical-center") {
                                    label.classList.add("vertical-center-label");
                                    tag.classList.add("vertical-center-element");
                                }
                                else if (format === "label-top") {
                                    label.classList.add("top");
                                }
                            }
                            if ("typecast" in element) this.typecasts.push({name: element.name, typecast: element.typecast});
                        }
                    }
                    __add_tag_attributes(element, tag);
                    if ("id" in element) this.id2element[element.id] = {element: tag, type: "element"};
                }

                return
            }
            container_level--;
        }

        for (const row of template) __iterate_template(row, parent);

        document.querySelectorAll(".form-container-collapsible").forEach(c => {
            c.addEventListener("click", e => {
                e.target.classList.toggle("active");
                const content = e.target.nextElementSibling;
                content.style.display = content.style.display === "block" ? "none" : "block";
            });
        });
    }

    // Iterate over data.  If a corresponding field (in the form) is found, set the value.
    // In case of a select, it is possible to limit the number of options, depending on the category
    populate = async (data, meta = null) => {
        for (let [field_name, value] of Object.entries(data)) {
            const field = this.form.querySelector(`[name=${field_name}]`);
            if (field) {
                if (field.type === "checkbox") {
                    field.checked = value;
                } else if (field.classList.contains("select2-hidden-accessible")) { // select2 type
                    await $(`[name=${field_name}]`).val(value).trigger("change");
                } else if (field.classList.contains("ql-container") && "quill" in meta && field_name in meta.quill) { // quill html editor
                    await meta.quill[field_name].clipboard.dangerouslyPasteHTML(value);
                } else if (field.type === "select-one") {
                    if (meta && "keyed_option" in meta && field_name in meta.keyed_option) {
                        if ("key_field" in meta.keyed_option[field_name]) {
                            const key_value = data[meta.keyed_option[field_name].key_field];
                            if (key_value) {
                                const options = meta.keyed_option[field_name][key_value];
                                field.innerHTML = "";
                                for (const option of options) field.add(new Option(meta.label[field_name][option], option, value === option, value === option));
                            }
                        }
                    } else if (meta && "option" in meta && field_name in meta.option) {
                        field.innerHTML = "";
                        for (const item of meta.option[field_name]) field.add(new Option(item.label, item.value, value === item.value, value === item.value));
                    }
                } else {
                    if (meta && "label" in meta && field_name in meta.label) value = meta.label[field_name][value];
                    field.value = value;
                }
            }
        }
    }

    // Get the value of all html elements with a "name" attribute
    // All checkboxes are present with a true or false value
    // If required (depending on the template) a value can be typecasted.
    get_data = () => {
        const form_data = Object.fromEntries(new FormData(this.form));
        // checkboxes are present only when selected and have the value "on" => convert
        this.form.querySelectorAll("input[type='checkbox']").forEach(c => {
            if ("name" in c) form_data[c.name] = c.name in form_data
        })
        // if a field needs to be typecasted, e.g. from string to int
        for (const t of this.typecasts) {
            if (t.typecast === "integer") form_data[t.name] = parseInt(form_data[t.name]);
        }
        return form_data;
    }

    element = id => this.id2element[id].element;

    show = id => {
        if (this.id2element[id].type === "element") this.id2element[id].element.closest("div.form-element").hidden = false;
        else if (this.id2element[id].type === "group") this.id2element[id].element.hidden = false;
    }

}