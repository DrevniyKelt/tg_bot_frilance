function initSwipeStage() {
  const stage = document.querySelector("[data-swipe-stage]");
  const cards = Array.from(document.querySelectorAll("[data-swipe-card]"));
  const railItems = Array.from(document.querySelectorAll("[data-swipe-target]"));
  const toast = document.querySelector("[data-swipe-toast]");
  const matchModal = document.querySelector("[data-swipe-match]");
  const matchTitle = document.querySelector("[data-swipe-match-title]");
  const matchCopy = document.querySelector("[data-swipe-match-copy]");
  const matchLink = document.querySelector("[data-swipe-match-link]");
  const confettiLayer = document.querySelector("[data-swipe-confetti]");
  const filterForm = document.querySelector("[data-swipe-filter-form]");
  if (!stage || !cards.length) return;

  let activeIndex = 0;
  let pointerId = null;
  let startX = 0;
  let currentX = 0;
  let dragging = false;
  let dragInput = null;

  const target = stage.getAttribute("data-target") || "executors";
  const sourceOrderId = stage.getAttribute("data-source-order-id") || "";
  const labels = {
    matchTitle: stage.getAttribute("data-match-title") || "Match",
    matchCopy: stage.getAttribute("data-match-copy") || "",
    accepted: stage.getAttribute("data-accepted-copy") || "",
    rejected: stage.getAttribute("data-rejected-copy") || "",
    emptyTitle: stage.getAttribute("data-empty-title") || "",
    emptyCopy: stage.getAttribute("data-empty-copy") || "",
    openChat: stage.getAttribute("data-open-chat-label") || "Open",
  };

  let toastTimer = null;

  const setToast = (text = "", timeoutMs = 1800) => {
    if (!toast) return;
    toast.textContent = text;
    if (toastTimer) window.clearTimeout(toastTimer);
    if (text && timeoutMs > 0) {
      toastTimer = window.setTimeout(() => {
        toast.textContent = "";
      }, timeoutMs);
    }
  };

  const launchConfetti = () => {
    if (!confettiLayer) return;
    confettiLayer.innerHTML = "";
    for (let index = 0; index < 24; index += 1) {
      const piece = document.createElement("span");
      piece.className = "swipe-confetti";
      piece.style.left = `${8 + Math.random() * 84}%`;
      piece.style.animationDelay = `${Math.random() * 0.25}s`;
      piece.style.background = ["#1376f3", "#ffcf69", "#2e8b57", "#ff8f5a"][index % 4];
      piece.style.transform = `rotate(${Math.random() * 180}deg)`;
      confettiLayer.appendChild(piece);
    }
    window.setTimeout(() => {
      confettiLayer.innerHTML = "";
    }, 2200);
  };

  const updateDeck = () => {
    cards.forEach((card, index) => {
      card.classList.remove("is-active", "is-next", "is-rest", "is-gone");
      if (index < activeIndex) {
        card.classList.add("is-gone");
        return;
      }
      if (index === activeIndex) card.classList.add("is-active");
      else if (index === activeIndex + 1) card.classList.add("is-next");
      else card.classList.add("is-rest");
      card.style.transform = "";
      card.style.opacity = "";
      card.dataset.swipeState = "";
    });

    railItems.forEach((item, index) => {
      item.classList.toggle("is-active", index === activeIndex);
    });

    const exhausted = activeIndex >= cards.length;
    stage.classList.toggle("is-empty", exhausted);
    if (exhausted) {
      setToast(`${labels.emptyTitle}. ${labels.emptyCopy}`.trim(), 0);
    }
  };

  const activeCard = () => cards[activeIndex] || null;

  const renderDrag = (offsetX) => {
    const card = activeCard();
    if (!card) return;
    const rotation = offsetX / 18;
    card.style.transform = `translateX(${offsetX}px) rotate(${rotation}deg)`;
    card.style.opacity = String(Math.max(0.78, 1 - Math.abs(offsetX) / 520));
    if (offsetX > 30) card.dataset.swipeState = "accept";
    else if (offsetX < -30) card.dataset.swipeState = "reject";
    else card.dataset.swipeState = "";
  };

  const openMatchModal = (payload) => {
    if (!matchModal || !matchTitle || !matchCopy || !matchLink) return;
    matchTitle.textContent = labels.matchTitle;
    matchCopy.textContent = payload.status_label || labels.matchCopy;
    matchLink.textContent = labels.openChat;
    matchLink.href = payload.chat_url;
    matchModal.hidden = false;
    window.setTimeout(() => {
      matchModal.hidden = true;
    }, 7200);
  };

  const closeMatchModal = () => {
    if (!matchModal) return;
    matchModal.hidden = true;
  };

  const persistDecision = async (card, direction) => {
    const formData = new FormData();
    formData.set("direction", direction);
    if (sourceOrderId) formData.set("source_order_id", sourceOrderId);
    const response = await fetch(`/swipe/decision/${target}/${card.getAttribute("data-card-id")}`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) return null;
    return response.json();
  };

  const advance = async (direction) => {
    const card = activeCard();
    if (!card) return;
    const isAccept = direction === "accept";
    card.classList.add(isAccept ? "is-dismissed-right" : "is-dismissed-left");
    card.dataset.swipeState = isAccept ? "accept" : "reject";
    setToast(isAccept ? labels.accepted : labels.rejected);

    window.requestAnimationFrame(() => {
      activeIndex += 1;
      updateDeck();
    });

    try {
      const payload = await persistDecision(card, direction);
      if (payload?.matched && payload.chat_url) {
        launchConfetti();
        openMatchModal(payload);
        setToast(labels.matchTitle);
      } else if (payload?.status_label) {
        setToast(payload.status_label);
      }
    } catch (error) {
      console.error(error);
    }
  };

  const releaseDrag = () => {
    const card = activeCard();
    dragging = false;
    pointerId = null;
    dragInput = null;
    if (!card) return;
    card.classList.remove("is-dragging");
    const threshold = Math.max(110, card.offsetWidth * 0.18);
    if (currentX >= threshold) {
      card.style.transform = `translateX(${Math.max(currentX, window.innerWidth)}px) rotate(18deg)`;
      card.style.opacity = "0.1";
      advance("accept");
    } else if (currentX <= -threshold) {
      card.style.transform = `translateX(-${Math.max(Math.abs(currentX), window.innerWidth)}px) rotate(-18deg)`;
      card.style.opacity = "0.1";
      advance("reject");
    } else {
      card.style.transform = "";
      card.style.opacity = "";
      card.dataset.swipeState = "";
    }
    currentX = 0;
  };

  const onPointerMove = (event) => {
    if (!dragging || dragInput !== "pointer" || event.pointerId !== pointerId) return;
    currentX = event.clientX - startX;
    renderDrag(currentX);
  };

  const onPointerUp = (event) => {
    if (!dragging || dragInput !== "pointer" || event.pointerId !== pointerId) return;
    releaseDrag();
  };

  let mouseDown = false;

  const onMouseMove = (event) => {
    if (!mouseDown || !dragging || dragInput !== "mouse") return;
    currentX = event.clientX - startX;
    renderDrag(currentX);
  };

  const onMouseUp = () => {
    if (!mouseDown || !dragging || dragInput !== "mouse") return;
    mouseDown = false;
    releaseDrag();
  };

  railItems.forEach((item, index) => {
    item.addEventListener("click", () => {
      activeIndex = index;
      setToast("", 0);
      updateDeck();
    });
  });

  document.querySelectorAll("[data-swipe-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const direction = button.getAttribute("data-swipe-action");
      if (direction === "accept" || direction === "reject") {
        advance(direction);
      }
    });
  });

  document.querySelectorAll("[data-swipe-match-close]").forEach((button) => {
    button.addEventListener("click", closeMatchModal);
  });

  document.querySelectorAll("[data-swipe-autosubmit]").forEach((control) => {
    control.addEventListener("change", () => {
      if (filterForm) filterForm.submit();
    });
  });

  cards.forEach((card) => {
    card.addEventListener("pointerdown", (event) => {
      if (event.pointerType === "mouse") return;
      if (card !== activeCard()) return;
      dragging = true;
      dragInput = "pointer";
      pointerId = event.pointerId;
      startX = event.clientX;
      currentX = 0;
      card.classList.add("is-dragging");
      card.setPointerCapture(event.pointerId);
    });

    card.addEventListener("pointermove", onPointerMove);
    card.addEventListener("pointerup", onPointerUp);
    card.addEventListener("pointercancel", onPointerUp);
    card.addEventListener("mousedown", (event) => {
      if (card !== activeCard()) return;
      dragging = true;
      mouseDown = true;
      dragInput = "mouse";
      pointerId = "mouse";
      startX = event.clientX;
      currentX = 0;
      card.classList.add("is-dragging");
      event.preventDefault();
    });
  });

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);

  updateDeck();
}

document.addEventListener("DOMContentLoaded", initSwipeStage);
