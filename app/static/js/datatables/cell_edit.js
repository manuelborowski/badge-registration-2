import {AlertPopup} from "../common/popup.js";

export class CellEdit {
    select_options = {}; // dict of columnnumber => dict of value => label
    columns = {}; // columnnumber => {type, options, ...}

    constructor(table, template, changed_cb) {
        this.table = table;
        this.update_cb = changed_cb
        this.input_css = "celledit-input";
        for (let i = 0; i < template.length; i++) {
            if ("celledit" in template[i]) {
                const celledit = template[i].celledit;
                this.columns[i] = {type: celledit.type}
                if (["select", "bool"].includes(celledit.type)) {
                    this.columns[i].options = [];
                    this.select_options[i] = {};
                    celledit.options.forEach(o => {
                        this.columns[i].options.push({value: o[0], display: o[1]});
                        this.select_options[i][o[0]] = o[1];
                    });
                }
            }
        }
        if (this.columns !== {}) {
            this.attach_handler();
        }
    }

    attach_handler = () => {
        if (this.table != null) {
            $(this.table.table().body()).on('click', 'td', (e) => {
                const $td = $(e.currentTarget);
                const column_index = this.table.column($td).index();
                if (column_index in this.columns) {
                    //If the cell contains an input or select element, ignore additional mouseclicks
                    if (!$td.find('input').length && !$td.find('select').length) {
                        const old_value = this.sanitize_value(this.table.cell($td).data());
                        this.create_input_element($td, this.columns[column_index], old_value);
                    }
                }
            });
        }
    }

    create_input_element = ($target, column_config, old_value) => {
        let $edit_element = null;
        switch (column_config.type) {
            case "select":
            case "bool":
                const $select = $(`<select class="${this.input_css}"></select>`);
                $.each(column_config.options, function (index, option) {
                    const selected = old_value === option.value ? "selected" : "";
                    const $option_element = $(`<option value=${option.value} ${selected} style="z-index: 1000">${option.display}</option>`);
                    $select.append($option_element);
                });
                $select.on("change", this.update);
                // The span is required because in Edge, there is a gap between the select and the options, which causes the mouseleave to trigger too early.
                $edit_element = $(`<span id="wrapper" style="height:30px; display:inline-block">`).append($select);
                $($target).html($edit_element);
                break;
            case "text-confirmkey": // text input w/ confirm (old)
            case "int-confirmkey": // integer input w/ confirm (old)
            case "text": // text input w/ confirm
            case "int": // integer input w/ confirm
                const $text = $(`<input class="${this.input_css}" value="${old_value}">`);
                $text.on("keyup", e => {
                    if (e.keyCode === 13) this.update(e)
                    else if (e.keyCode === 27) this.cancel($target, old_value)
                });
                $($target).html($text);
                $text[0].focus();
                $text[0].setSelectionRange($text.val().length, $text.val().length);
                $edit_element = $text;
                break;
            case "date":
                const $date = $(`<input class="${this.input_css}" value="${old_value}" type="date">`);
                $($target).html($date);
                $edit_element = $date;
                $date.on("change", this.update);
                break;
            default:
                break;
        }
        if ($edit_element) {
            $edit_element.attr("data-type", column_config.type);
            $edit_element.on("mouseleave", e => {
                const $td = $(e.currentTarget.closest("td"))
                this.cancel($td, old_value)
            })
        }
    }

    // event points to the element inside the cell, e.g. select
    update = async event => {
        const $dt_row = this.table.row(event.currentTarget.closest("tr")); // parentNode.parentNode: tr element
        const $td = $(event.currentTarget.closest("td"))
        const $dt_cell = this.table.cell($td); // parentNode: td element
        const column_index = this.table.column($td).index();
        const column_config = this.columns[column_index];
        let old_value = $dt_cell.data();
        let new_value = event.currentTarget.value;
        if (column_config.type === "select") {
            $dt_cell.data(this.select_options[column_index][new_value]);
        } else if (column_config.type === "date") {
            $dt_cell.data(new_value);
        } else if (column_config.type === "bool") {
            $dt_cell.data(this.select_options[column_index][new_value]);
            new_value = new_value === "true";
        } else if (["text-confirmkey", "text"].includes(column_config.type)) {
            $dt_cell.data(new_value);
        } else if (["int", "int-confirmkey"].includes(column_config.type)) {
            new_value = parseInt(new_value);
            old_value = parseInt(old_value);
            if (isNaN(new_value)) {
                new AlertPopup("warning", "Je moet een getal ingeven, aub");
                new_value = old_value;
            }
            $dt_cell.data(new_value);
        }
        this.update_cb($dt_row, column_index, new_value, old_value);
    }

    cancel = (cell, old_value) => {
        const column_index = this.table.cell($(cell)).index().column;
        if (column_index in this.select_options) old_value = this.select_options[column_index][old_value];
        $(cell).html(old_value);
    }

    sanitize_value(value) {
        if (typeof (value) === "number") return isNaN(value) ? "" : value;
        if (typeof (value) === 'undefined' || value === null || value.length < 1) return "";
        if (typeof (value) === "string") value = value.replace(/'/g, "&#39;");
        return value;
    }
}