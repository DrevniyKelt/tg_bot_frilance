function syncTagPickers() {
  document.querySelectorAll("[data-tag-picker]").forEach((picker) => {
    const inputId = picker.getAttribute("data-input-id");
    const hiddenInput = document.getElementById(inputId);
    if (!hiddenInput) return;

    const selected = new Set(
      (hiddenInput.value || "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    );

    const refresh = () => {
      picker.querySelectorAll("[data-tag-value]").forEach((button) => {
        const value = button.getAttribute("data-tag-value");
        button.classList.toggle("is-selected", selected.has(value));
      });
      hiddenInput.value = Array.from(selected).join(",");
    };

    picker.querySelectorAll("[data-tag-value]").forEach((button) => {
      button.addEventListener("click", () => {
        const value = button.getAttribute("data-tag-value");
        if (selected.has(value)) {
          selected.delete(value);
        } else if (selected.size < 30) {
          selected.add(value);
        }
        refresh();
      });
    });

    refresh();
  });
}

function wireBudgetPreview() {
  const input = document.querySelector("[data-budget-input]");
  const preview = document.querySelector("[data-budget-preview]");
  if (!input || !preview) return;

  const executor = preview.querySelector("[data-preview-executor]");
  const client = preview.querySelector("[data-preview-client]");
  const fee = Number(preview.getAttribute("data-fee-percent") || "1");
  const formatter = new Intl.NumberFormat("ru-RU");

  const render = () => {
    const budget = Number(input.value || 0);
    const clientTotal = budget + budget * (fee / 100);
    executor.textContent = formatter.format(budget);
    client.textContent = formatter.format(clientTotal);
  };

  input.addEventListener("input", render);
  render();
}

function wireNavDropdowns() {
  const dropdowns = document.querySelectorAll("[data-nav-dropdown]");
  if (!dropdowns.length) return;

  const closeAll = (except) => {
    dropdowns.forEach((dropdown) => {
      if (dropdown === except) return;
      dropdown.classList.remove("is-open");
      const trigger = dropdown.querySelector("[data-nav-dropdown-trigger]");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  };

  dropdowns.forEach((dropdown) => {
    const trigger = dropdown.querySelector("[data-nav-dropdown-trigger]");
    if (!trigger) return;

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      const isOpen = dropdown.classList.contains("is-open");
      closeAll(dropdown);
      dropdown.classList.toggle("is-open", !isOpen);
      trigger.setAttribute("aria-expanded", String(!isOpen));
    });
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (target.closest("[data-nav-dropdown]")) return;
    closeAll(null);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    closeAll(null);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  syncTagPickers();
  wireBudgetPreview();
  wireNavDropdowns();
});
