function initCommunityTabs() {
  const panel = document.querySelector("[data-community-panel]");
  const tabs = document.querySelectorAll("[data-community-tab]");
  if (!panel || !tabs.length) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      const current = tab.classList.contains("is-active");
      const href = tab.getAttribute("href");
      const direction = tab.getAttribute("data-community-direction") || "right";
      if (current || !href) return;
      event.preventDefault();
      panel.classList.remove("is-flipping-left", "is-flipping-right");
      panel.classList.add(direction === "left" ? "is-flipping-left" : "is-flipping-right");
      window.setTimeout(() => {
        window.location.href = href;
      }, 240);
    });
  });
}

document.addEventListener("DOMContentLoaded", initCommunityTabs);
