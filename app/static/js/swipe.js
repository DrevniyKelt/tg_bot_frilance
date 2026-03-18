function initSwipeStage() {
  const cards = Array.from(document.querySelectorAll("[data-swipe-card]"));
  const railItems = Array.from(document.querySelectorAll("[data-swipe-target]"));
  if (!cards.length) return;

  let activeIndex = 0;

  const setActive = (index) => {
    activeIndex = (index + cards.length) % cards.length;
    cards.forEach((card, cardIndex) => {
      card.classList.toggle("is-active", cardIndex === activeIndex);
    });
    railItems.forEach((item, itemIndex) => {
      item.classList.toggle("is-active", itemIndex === activeIndex);
    });
  };

  railItems.forEach((item, index) => {
    item.addEventListener("click", () => setActive(index));
  });

  document.querySelectorAll("[data-swipe-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const direction = button.getAttribute("data-swipe-action");
      setActive(direction === "next" ? activeIndex + 1 : activeIndex - 1);
    });
  });

  setActive(0);
}

document.addEventListener("DOMContentLoaded", initSwipeStage);
