const notification = document.getElementById("notification");

const ws = new WebSocket("ws://127.0.0.1:8765/ws");


ws.onopen = () => {
    console.log("Connected to overlay server");
};


ws.onclose = () => {
    console.log("Overlay connection closed");
};


ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};


ws.onmessage = (message) => {
    try {
        const event = JSON.parse(message.data);

        console.log("Overlay data:", event);

        const data = event.data;

        if (!data) {
            return;
        }

        showDonation(data);

    } catch (error) {
        console.error("Invalid WebSocket message:", error);
    }
};


function showDonation(data) {

    const notification = document.getElementById("notification");

    notification.innerHTML = `
        <div class="notification">

            <div class="title">
                New Gift!
            </div>

            <div class="amount">
                ${data.amount ?? ""} ${data.currency ?? ""}
            </div>

            <div class="name">
                ${data.name ?? data.username ?? ""}
            </div>

            ${
                data.message
                    ? `<div class="message">${data.message}</div>`
                    : ""
            }

        </div>
    `;


    /*
     * Random position
     */

    const marginX = 12;
    const marginY = 12;

    const maxX = 100 - marginX;
    const maxY = 100 - marginY;

    const x =
        marginX +
        Math.random() * (maxX - marginX);

    const y =
        marginY +
        Math.random() * (maxY - marginY);


    notification.style.left = `${x}%`;
    notification.style.top = `${y}%`;


    notification.classList.add("show");


    setTimeout(() => {
        notification.classList.remove("show");
    }, 10000);
}