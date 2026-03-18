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

document.addEventListener("DOMContentLoaded", () => {
  syncTagPickers();
  wireBudgetPreview();
});
