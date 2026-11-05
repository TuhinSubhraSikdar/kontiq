"use strict";

// Return focus to the sidebar toggle after Bootstrap closes the mobile menu.
document.addEventListener("hidden.bs.offcanvas", (event) => {
    if (event.target.id === "appSidebar") {
        document.querySelector('[data-bs-target="#appSidebar"]')?.focus();
    }
});
