// create a popup the displayes a message with a specified bordercolor
// the popup disappears after a delay (5s) or when clicked next to the popup
export class AlertPopup {
    timer_id = null;
    constructor(status = "ok", msg, delay = 5000) {
        if (window["bootbox"]) {
            if (this.timer_id !== null) clearTimeout(timer.timer_id);
            if (delay > 0) this.timer_id = setTimeout(() => this.dialog.modal("hide"), delay);
            this.dialog = bootbox.dialog({
                size: "large",
                backdrop: true,
                message: msg,
                closeButton: false,
                className: status === "ok" ? "alert-popup timed-popup-ok" : status === "warning" ? "alert-popup timed-popup-warning" : "alert-popup timed-popup-error"
            })
        } else {
            alert(msg)
        }
    }

    hide() {
        this.dialog.modal("hide");
    }
}
