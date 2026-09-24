(function () {
  "use strict";

  const installCommand = 'pipx install "pyffmpegcore==0.3.0"';

  async function copyText(value) {
    if (window.navigator?.clipboard?.writeText) {
      await window.navigator.clipboard.writeText(value);
      return;
    }

    const field = document.createElement("textarea");
    field.value = value;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    if (!copied) throw new Error("Copy command was rejected");
  }

  function initializeCopyButtons() {
    document.querySelectorAll("[data-pfc-copy]").forEach((button) => {
      if (button.dataset.pfcReady === "true") return;
      button.dataset.pfcReady = "true";
      button.addEventListener("click", async () => {
        const original = button.textContent;
        try {
          await copyText(installCommand);
          button.textContent = "COPIED / READY";
        } catch (_error) {
          button.textContent = "COPY FAILED / SELECT COMMAND";
        }
        window.setTimeout(() => {
          button.textContent = original;
        }, 1800);
      });
    });
  }

  function updateScrollableTables() {
    document.querySelectorAll(".md-typeset__scrollwrap").forEach((wrapper) => {
      if (wrapper.scrollWidth > wrapper.clientWidth + 1) {
        wrapper.tabIndex = 0;
        wrapper.setAttribute("role", "region");
        wrapper.setAttribute("aria-label", "Scrollable data table");
      } else {
        wrapper.removeAttribute("tabindex");
        wrapper.removeAttribute("role");
        wrapper.removeAttribute("aria-label");
      }
    });
  }

  function initializePage() {
    initializeCopyButtons();
    updateScrollableTables();
  }

  window.addEventListener("resize", updateScrollableTables);

  if (typeof document$ !== "undefined") {
    document$.subscribe(initializePage);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializePage);
  } else {
    initializePage();
  }
})();
