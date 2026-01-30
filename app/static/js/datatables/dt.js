import {return_render_ellipsis} from "./ellipsis.js";
import {socketio} from "../common/socketio.js";
import {AlertPopup} from "../common/popup.js";
import {busy_indication_off, busy_indication_on, fetch_post, fetch_update} from "../common/common.js";
import {base_init} from "../base.js";
import {ContextMenu} from "../common/context_menu.js";
import {FilterMenu} from "../common/filter_menu.js";
import {CellEdit} from "./cell_edit.js";
import {ColumnVisibility} from "../common/column_visibility.js";

export let datatable_column2index = {};
export let ctx = {table: null};

//If not exactly one checkbox is selected, display warning and return false, else return true
function checkbox_is_exactly_one_selected() {
    let nbr_checked = 0;
    $(".chbx_all").each(function () {
        if (this.checked) nbr_checked++;
    });
    if (nbr_checked !== 1) new AlertPopup("warning", "U moet minstens één lijn selecteren")
    return nbr_checked === 1
}

//If one or more checkboxes are checked, return true.  Else display warning and return false
function checkbox_is_at_least_one_selected() {
    let nbr_checked = 0;
    $(".chbx_all").each(function () {
        if (this.checked) nbr_checked++;
    });
    if (nbr_checked === 0) new AlertPopup("warning", "U hebt niets geselecteerd, probeer nogmaals");
    return nbr_checked !== 0
}

export function checkbox_get_ids() {return Array.from(document.querySelectorAll(".chbx_all:checked")).map(c => c.value);}

export function datatable_clear_checked_boxes() {
    $(".chbx_all").prop('checked', false);
    $("#select_all").prop('checked', false);
}

// If checkboxes are checked, return the ids of the selected rows
// Else, return the id of row the mouse pointer is on.
export const mouse_get_ids = mouse_event => {
    let ids = checkbox_get_ids();
    if (ids.length === 0) ids = [mouse_event.target.closest("tr").id];
    return ids;
}

export function datatable_row_data_from_id(id) {return ctx.table.row(`#${id}`).data();}

export const datatable_row_data_from_target = target => {
    return ctx.table.row(target.target.closest("tr")).data();
}

export function datatable_update_cell(row_id, column_name, value) {
    let row_idx = ctx.table.row(`#${row_id}`).index();
    let column_idx = datatable_column2index[column_name];
    if (column_idx !== undefined) {
        ctx.table.cell(row_idx, column_idx).data(value).draw();
    } else {
        ctx.table.rows(row_idx).data()[0][column_name] = value;
        ctx.table.rows(row_idx).invalidate("data").draw(false);
    }
}

export function datatable_filter(column_name, value) {
    let column_idx = datatable_column2index[column_name];
    ctx.table.column(column_idx).search(value).draw();
}

export function datatable_rows_add(rows) {
    ctx.table.rows.add(rows).draw();
}

export function datatable_rows_delete(ids) {
    ids.forEach(id => ctx.table.row(`#${id}`).remove());
    ctx.table.draw(false);
}

export function datatable_table_add(table) {
    ctx.table.clear().rows.add(table).draw();
}

export function datatable_remove_table() {
    document.querySelector(".container-fluid").innerHTML = "";
}

export function datatable_reload_table() {
    ctx.table.ajax.reload();
}

const __filter_changed_cb = (id, value) => {
    if (ctx.server_side) datatable_reload_table();
}

export const datatables_init = ({config = null, context_menu_items = [], filter_menu_items = [], action_menu_items = [], callbacks = {}, initial_data = null} = {}) => {
    // If a table already exist, remove it
    if (ctx.table) {
        ctx.table.destroy();
        $('#datatable').empty();
    }
    config = config || table_config; // default, use config via server -> view -> render_template(...) or overwrite from caller
    ctx.config = config;
    const table = document.createElement("table");
    table.id = "datatable";
    const th = document.createElement("thead");
    table.appendChild(th);
    const tr = document.createElement("tr");
    th.appendChild(tr);
    ctx.config.template.forEach(i => {
        const th = document.createElement("th");
        tr.appendChild(th);
        if (i.name === "row_action") {
            const input = document.createElement("input");
            th.appendChild(input);
            input.type = "checkbox";
            input.id = "select_all";
        } else {
            th.innerHTML = i.name;
            if (i.tooltip) th.title = i.tooltip;
        }
    });
    document.querySelector(".container-fluid").innerHTML = "";
    document.querySelector(".container-fluid").appendChild(table);
    ctx.cell_to_color = "color_keys" in ctx.config ? ctx.config.cell_color.color_keys : null;
    ctx.suppress_cell_content = "color_keys" in ctx.config ? ctx.config.cell_color.supress_cell_content : null;

    ctx.context_menu = new ContextMenu(document.querySelector("#datatable"), context_menu_items);
    ctx.context_menu.subscribe_get_ids(mouse_get_ids);
    ctx.filter_menu = new FilterMenu(document.querySelector(".filter-menu-placeholder"), filter_menu_items, __filter_changed_cb, ctx.config.view);

    ctx.server_side = initial_data === null; // Get data from te server

    // when columns are hidden, this array maps the real column index on the visible column index
    let column_shifter = [];
    const __calc_column_shift = () => {
        column_shifter = [];
        let shift = 0;
        for (let i = 0; i < ctx.table.columns().count(); i++) {
            if (ctx.table.column(i).visible()) {
                column_shifter.push(i - shift);
            } else {
                shift++;
                column_shifter.push(null);
            }
        }
    }

    //Bugfix to repeat the table header at the bottom
    $("#datatable").append(
        $('<tfoot/>').append($("#datatable thead tr").clone())
    );

    const render_display = (data, typen, full, meta, v) => {
        let values = [];
        let color = null;
        for (const f of v.fields) {
            let value = full[f.field];
            if ("colors" in f) color = f.colors[value];
            if ("labels" in f) value = f.labels[value];
            if ("bool" in f) value = value === true ? "&#10003;" : "";
            values.push(value);
        }
        var template = values[0];
        if ("template" in v) {
            template = v.template;
            for (let i = 0; i < values.length; i++) template = template.replaceAll(`%${i}%`, values[i]);
        }
        if (color) {
            return `<div style="background:${color};">${template}</div>`
        } else {
            return template
        }
    }

    const render = (v) => {
        if ("ellipsis" in v) return_render_ellipsis(v.ellipsis.cutoff, v.ellipsis.wordbreak, true);
        if ("bool" in v) return (data, type, full, meta) => data === true ? "&#10003;" : "";
        if ("label" in v) return (data, type, full, meta) => v.label.labels[data]
        if ("color" in v) {
            const render = "render" in v ? v.render : null;
            v.render = function (data, type, full, meta) {
                if (render) data = render(data);
                return `<div style="background:${v.color.colors[ctx.table.cell(meta.row, meta.col).data()]};">${data}</div>`
            }
        }
        if ("less" in v) return (data, type, full, meta) => data < v.less.than ? ("then" in v.less ? v.less.then : data) : ("else" in v.less ? v.less.else : data)
        if ("display" in v) return (data, type, full, meta) => render_display(data, type, full, meta, v.display);
        if ("equal" in v) return (data, type, full, meta) => data === v.equal.to ? render_display(data, type, full, meta, v.equal.then) : render_display(data, type, full, meta, v.equal.else);
    };

    // check special options in the columns
    $.each(ctx.config.template, (i, v) => {
        v.render = render(v);
        datatable_column2index[v.data] = i;
    })

    let datatable_config = {
        autoWidth: false,
        stateSave: true,
        stateDuration: 0,
        pagingType: "full_numbers",
        columns: ctx.config.template,
        language: {url: "static/datatables/dutch.json"},
        layout: {
            topStart: ["info"],
            topEnd: "search",
            bottomStart: ["pageLength", "paging"],
            bottomEnd: null
        },
        lengthMenu: [100, 500, 1000, 2000],
        pageLength: 2000,
        // This callback is executed for every row, but only when the table is created.  If e.g. a cell needs to be highlighted depending on a value, and that value does not change.
        createdRow: function (row, data, dataIndex, cells) {
            // update, if required, data before checking on row_color and cell_color
            if (callbacks.created_row) callbacks.created_row(row, data, dataIndex, cells);
            // in format_data, it is possible to tag a line with a different backgroundcolor
            if (data.row_color) $(row).attr("style", `background-color:${data.row_color};`);
            if (data.cell_color) {
                for (const [cn, cc] of Object.entries(data.cell_color)) {
                    const ci = datatable_column2index[cn];
                    $(cells[ci]).attr("style", `background-color: ${cc};`);
                }
            }
        },
        // This callback is executed each time the table is reloaded or a value is changed.
        rowCallback: function (row, data, displayNum, displayIndex, dataIndex) {
            if (data.row_action !== null) row.cells[0].innerHTML = `<input type='checkbox' class='chbx_all' name='chbx' value='${data.row_action}' ${data.disable_selectbox ? "disabled" : ""}>`
            // celledit of type select: overwrite cell content with label from optionlist
            if (cell_edit.select_options) {
                for (const [column, select] of Object.entries(cell_edit.select_options)) {
                    if (column_shifter[column] !== null) {
                        row.cells[column_shifter[column]].innerHTML = select[row.cells[column_shifter[column]].innerHTML];
                    }
                }
            }
            if (callbacks.row_callback) {
                const res = callbacks.row_callback(data, row);
                if (res) res.forEach(c => row.cells[c.index].innerHTML = c.value);
            }
        },
        preDrawCallback: function (settings) {
            __calc_column_shift();
        },
        drawCallback: function (settings) {
            if (ctx.cell_to_color) {
                ctx.table.cells().every(function () {
                    if (this.data() in ctx.cell_to_color) {
                        $(this.node()).css("background-color", ctx.cell_to_color[this.data()]);
                        if (ctx.suppress_cell_content) $(this.node()).html("");
                    }
                });
            }
            if (callbacks.table_loaded) callbacks.table_loaded();
        },
        initComplete: function () {
            new ColumnVisibility(document.querySelector('.column-visible-placeholder'), ctx.config.template, (column, visible) => ctx.table.column(column).visible(visible), ctx.config.view);
            if ("width" in ctx.config) {
                const dt_container = document.querySelector("div.dt-container")
                dt_container.style.width = ctx.config.width;
                dt_container.style.marginLeft = "auto";
                dt_container.style.marginRight = "auto";
            }
        },
        stateSaveCallback: function (settings, data) {
            localStorage.setItem(`DatatableState-${ctx.config.view}`, JSON.stringify(data));
        },
        stateLoadCallback: function (settings, callback) {
            const state = localStorage.getItem(`DatatableState-${ctx.config.view}`);
            callback(JSON.parse(state));
        }
    }

    if (ctx.server_side) {
        datatable_config.ajax = async function (data, cb, settings) {
            busy_indication_on();
            let filters = ctx.filter_menu.filters;
            const ret = await fetch_post(`${ctx.config.view}.dt`, $.extend({}, data, {filters}));
            busy_indication_off();
            cb(ret);
        };
        datatable_config.serverSide = true;
    } else {
        datatable_config.serverSide = false;
        datatable_config.data = initial_data;
    }

    if ("default_order" in ctx.config) {
        datatable_config["order"] = [[ctx.config.default_order[0], ctx.config.default_order[1]]];
    }

    DataTable.type('num', 'className', 'dt-left');
    DataTable.type('date', 'className', 'dt-left');
    DataTable.defaults.column.orderSequence = ['desc', 'asc'];
    ctx.table = new DataTable('#datatable', datatable_config);

    // if columns are invisible, the column index in rowCallback is reduced, depending on the invisible columns.
    // create a translation table to go from actual column index to the reduced (with invisible columns) column index
    // the table is redrawn because hiding/displaying columns has impact on columns with ellipses
    ctx.table.on('column-visibility.dt', (e, settings, column, state) => {
        __calc_column_shift();
        ctx.table.draw();
    });

    const __cell_edit_changed_cb = async ($dt_row, column_index, new_value, old_value) => {
        const value = ctx.config.template[column_index].celledit.value_type === 'int' ? parseInt(new_value) : new_value; // deprecated, user type "int" and new_value is of type int
        const column_name = ctx.table.column(column_index).dataSrc()
        // update_cell_changed({id: $dt_row.data().DT_RowId, column: column_name, value});
        await fetch_update(`${ctx.config.view}.${ctx.config.view}`, {id: $dt_row.data().DT_RowId, [column_name]: value});
        if (callbacks.cell_edit) callbacks.cell_edit($dt_row.data().DT_RowId, column_name, value);
    }

    const cell_toggle_changed_cb = async (cell, row, value) => {
        await fetch_update(`${ctx.config.view}.${ctx.config.view}`, {id: row.data().DT_RowId, [cell.index().column]: value});
    }

    const cell_edit = new CellEdit(ctx.table, ctx.config.template, __cell_edit_changed_cb);

    //checkbox in header is clicked
    $("#select_all").change(function () {
        $(".chbx_all").prop('checked', this.checked);
    });
    base_init({action_menu_items});
    return ctx
}

