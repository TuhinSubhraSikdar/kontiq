"use strict";

// Return focus to the sidebar toggle after Bootstrap closes the mobile menu.
document.addEventListener("hidden.bs.offcanvas", (event) => {
    if (event.target.id === "appSidebar") {
        document.querySelector('[data-bs-target="#appSidebar"]')?.focus();
    }
});

// Keep spreadsheet-style queue selection predictable, including filtered lists.
const selectAll = document.querySelector("[data-select-all]");
const rowCheckboxes = [...document.querySelectorAll("[data-row-checkbox]")];

function syncSelectAll() {
    if (!selectAll) return;
    const selectedCount = rowCheckboxes.filter((checkbox) => checkbox.checked).length;
    selectAll.checked = rowCheckboxes.length > 0 && selectedCount === rowCheckboxes.length;
    selectAll.indeterminate = selectedCount > 0 && selectedCount < rowCheckboxes.length;
}

selectAll?.addEventListener("change", () => {
    rowCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectAll.checked;
    });
    syncSelectAll();
});

rowCheckboxes.forEach((checkbox) => checkbox.addEventListener("change", syncSelectAll));
