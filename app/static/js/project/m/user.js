import {fetch_get} from "../../common/common.js";

$(document).ready(async () => {
    const users = await fetch_get("user.user");
    const user_list = document.getElementById("user-list");
    for (const user of users) {
        user_list.innerHTML += `${user.username} ${user.last_name} ${user.first_name} <br>`
    }
});
