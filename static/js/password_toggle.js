(() => {
  function setState(btn, input) {
    const isText = input.type === "text";

    const eye = btn.querySelector(".js-eye");
    const eyeSlash = btn.querySelector(".js-eye-slash");

    if (eye) eye.classList.toggle("d-none", isText);
    if (eyeSlash) eyeSlash.classList.toggle("d-none", !isText);

    btn.setAttribute("aria-label", isText ? "Skryť heslo" : "Zobraziť heslo");
    btn.setAttribute("aria-pressed", String(isText));
  }

  function resolveInput(btn) {
    const sel = btn.getAttribute("data-password-toggle");
    if (sel) return document.querySelector(sel);
    return btn.closest(".input-group")?.querySelector("input");
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-password-toggle]");
    if (!btn) return;

    const input = resolveInput(btn);
    if (!input) return;

    input.type = input.type === "password" ? "text" : "password";
    setState(btn, input);

    input.focus({ preventScroll: true });
  });

  // init (kvôli autofill a správnemu ikonkovému stavu)
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-password-toggle]").forEach((btn) => {
      const input = resolveInput(btn);
      if (input) setState(btn, input);
    });
  });
})();
