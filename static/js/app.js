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
const proceedSelected = document.querySelector("[data-proceed-selected]");
const selectionSummary = document.querySelector("#selection-summary");

function syncSelectAll() {
    const selectableRows = rowCheckboxes.filter((checkbox) => !checkbox.disabled);
    const selectedCount = selectableRows.filter((checkbox) => checkbox.checked).length;
    if (selectAll) {
        selectAll.checked = selectableRows.length > 0 && selectedCount === selectableRows.length;
        selectAll.indeterminate = selectedCount > 0 && selectedCount < selectableRows.length;
        selectAll.disabled = selectableRows.length === 0;
    }
    if (proceedSelected) proceedSelected.disabled = selectedCount === 0;
    if (selectionSummary) {
        selectionSummary.innerHTML = selectedCount
            ? `<strong>${selectedCount} row${selectedCount === 1 ? "" : "s"} selected.</strong> Proceed sends them to the configured AI worker.`
            : "<strong>Select rows</strong> only when their brief is ready. Proceed sends them to the configured AI worker.";
    }
}

selectAll?.addEventListener("change", () => {
    rowCheckboxes.forEach((checkbox) => {
        if (!checkbox.disabled) checkbox.checked = selectAll.checked;
    });
    syncSelectAll();
});

rowCheckboxes.forEach((checkbox) => checkbox.addEventListener("change", syncSelectAll));
syncSelectAll();

// Persist the desktop navigation density without affecting the mobile drawer.
const sidebarCollapse = document.querySelector("[data-sidebar-collapse]");
const sidebarCollapsed = localStorage.getItem("kontiq-sidebar-collapsed") === "true";
document.body.classList.toggle("sidebar-collapsed", sidebarCollapsed);
sidebarCollapse?.setAttribute("aria-expanded", String(!sidebarCollapsed));
sidebarCollapse?.addEventListener("click", () => {
    const collapsed = document.body.classList.toggle("sidebar-collapsed");
    localStorage.setItem("kontiq-sidebar-collapsed", String(collapsed));
    sidebarCollapse.setAttribute("aria-expanded", String(!collapsed));
    sidebarCollapse.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
});

// Theme selection is applied in the document head to avoid a flash on load.
document.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
    const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("kontiq-theme", theme);
});

const globalSearch = document.querySelector("#global-search");
document.addEventListener("keydown", (event) => {
    const target = event.target;
    const isTyping = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;
    if (event.key === "/" && !isTyping && globalSearch) {
        event.preventDefault();
        globalSearch.focus();
    }
});

function showToast(message) {
    const toast = document.createElement("div");
    toast.className = "clipboard-toast";
    toast.setAttribute("role", "status");
    toast.textContent = message;
    document.body.appendChild(toast);
    window.setTimeout(() => toast.classList.add("is-visible"), 10);
    window.setTimeout(() => {
        toast.classList.remove("is-visible");
        window.setTimeout(() => toast.remove(), 180);
    }, 1800);
}

async function copyText(text) {
    try {
        await navigator.clipboard.writeText(text);
    } catch (_) {
        const helper = document.createElement("textarea");
        helper.value = text;
        helper.style.position = "fixed";
        helper.style.opacity = "0";
        document.body.appendChild(helper);
        helper.select();
        document.execCommand("copy");
        helper.remove();
    }
    showToast("Copied to clipboard");
}

document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", () => {
        const target = document.getElementById(button.dataset.copyTarget);
        if (target) copyText("value" in target ? target.value : target.textContent);
    });
});

const promptEditor = document.querySelector("[data-prompt-editor]");
if (promptEditor) {
    const promptInput = promptEditor.querySelector("#id_template");
    const preview = document.querySelector("[data-live-preview]");
    const saveStatus = document.querySelector("[data-save-status]");
    const draftKey = `kontiq-prompt-draft:${window.location.pathname}`;
    let draftTimer;

    const renderPreview = () => {
        if (!promptInput || !preview) return;
        preview.textContent = promptInput.value.replace(/{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}/g, (_, name) => `[${name.replaceAll("_", " ")}]`);
    };

    document.querySelectorAll("[data-insert-variable]").forEach((button) => {
        button.addEventListener("click", () => {
            if (!promptInput) return;
            const token = `{{ ${button.dataset.insertVariable} }}`;
            const start = promptInput.selectionStart;
            const end = promptInput.selectionEnd;
            promptInput.setRangeText(token, start, end, "end");
            promptInput.dispatchEvent(new Event("input", { bubbles: true }));
            promptInput.focus();
        });
    });

    promptInput?.addEventListener("input", () => {
        renderPreview();
        saveStatus?.classList.add("is-dirty");
        if (saveStatus) saveStatus.querySelector("strong").textContent = "Unsaved changes";
        window.clearTimeout(draftTimer);
        draftTimer = window.setTimeout(() => {
            localStorage.setItem(draftKey, promptInput.value);
            if (saveStatus) saveStatus.querySelector("strong").textContent = "Draft saved locally";
        }, 500);
    });

    document.querySelector("[data-copy-preview]")?.addEventListener("click", () => copyText(preview?.textContent || ""));
    renderPreview();
}
