(function () {
  "use strict";

  const installCommand =
    "pipx install git+https://github.com/OthmaneBlial/pyffmpegcore.git@04d1e7051295bbcc4fa137c1214bbf340bf5c4c0";

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

  if (typeof document$ !== "undefined") {
    document$.subscribe(initializeCopyButtons);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeCopyButtons);
  } else {
    initializeCopyButtons();
  }
})();
