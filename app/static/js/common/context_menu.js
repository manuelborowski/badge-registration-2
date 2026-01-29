
export class ContextMenu {
    item_ids = 0;
    get_ids_cb = null;
    postprocessing_cb = null;

    constructor(active_area, menu) {
        this.context_placeholder = document.createElement("div");
        this.context_placeholder.classList.add("context-menu-placeholder");
        this.menu = document.createElement("ul");
        this.context_placeholder.appendChild(this.menu);

        // create menu
        this.menu.innerHTML = "";
        for (const mi of menu) {
            if ("level" in mi && mi.level > current_user.level) continue; //skip entries when level of user is too low
            const li = document.createElement("li");
            this.menu.appendChild(li);
            const span = document.createElement("span");
            if(mi.type === "divider") {
                span.innerHTML = "--------------";
            } else if(mi.type === "text_input") {
                const input = document.createElement("input");
                span.appendChild(input);
            } else {
                li.onclick = () => this.item_clicked_with_cb(mi.cb);
                if ("iconscout" in mi) {
                    const i = document.createElement("i");
                    i.classList.add("uil", `uil-${mi.iconscout}`);
                    li.appendChild(i);
                }
                span.innerHTML = mi.label;
            }
            li.appendChild(span);
        }

        // right-mouse-click in the active-area will open the context menu
        document.addEventListener("contextmenu", e => {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (!active_area.contains(e.target)) return;
            let x = e.x, y = e.y;
            const win_width = window.innerWidth;
            const win_height = window.innerHeight;
            const menu_width = this.context_placeholder.offsetWidth;
            const menu_height = this.context_placeholder.offsetHeight;
            if (this.menu !== null) {
                if (x > (win_width - menu_width - this.menu.offsetWidth)) {
                    this.menu.style.left = "-200px";
                } else {
                    this.menu.style.left = "";
                    this.menu.style.right = "-200px";
                }
            }
            x = x > win_width - menu_width ? win_width - menu_width - 5 : x;
            y = y > win_height - menu_height ? e.pageY - menu_height - 5 : e.pageY;
            this.item_ids = []
            if (this.get_ids_cb) {
                this.item_ids = this.get_ids_cb(e);
            } else {
                console.log("context_active_area.addEventListener: no get_ids_cb configured")
            }
            this.context_placeholder.style.left = `${x}px`;
            this.context_placeholder.style.top = `${y}px`;
            document.querySelector("body").appendChild(this.context_placeholder);
            document.addEventListener("click", () => this.context_placeholder.remove());
        }, { capture: true });

    }

    subscribe_get_ids = cb => this.get_ids_cb = cb;

    subscribe_post_processing = cb => this.postprocessing_cb = cb;

    item_clicked_with_cb = cb => {
        cb(this.item_ids);
        if (this.postprocessing_cb) this.postprocessing_cb(self.item_ids);
    }
}
