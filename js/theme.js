/* Runs before stylesheets so saved/system appearance is set before first paint. */
(() => {
  "use strict";
  const key = "noise-appearance";
  const root = document.documentElement;
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const valid = (value) => ["light", "dark", "system"].includes(value);
  let mode = "system";
  try {
    const saved = localStorage.getItem(key);
    if (valid(saved)) mode = saved;
  } catch { /* Storage may be disabled; appearance still works for this page. */ }

  function apply() {
    const dark = mode === "dark" || (mode === "system" && system.matches);
    root.dataset.theme = dark ? "dark" : "light";
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#111512" : "#fbfaf7");
    const select = document.getElementById("theme-mode");
    if (select) select.value = mode;
  }
  apply();
  system.addEventListener("change", apply);
  window.addEventListener("storage", (event) => {
    if (event.key !== key && event.key !== null) return;
    mode = valid(event.newValue) ? event.newValue : "system";
    apply();
  });
  document.addEventListener("DOMContentLoaded", () => {
    const control = document.querySelector(".theme-control");
    const select = document.getElementById("theme-mode");
    if (!control || !select) return;
    control.hidden = false;
    select.value = mode;
    select.addEventListener("change", () => {
      mode = valid(select.value) ? select.value : "system";
      try {
        if (mode === "system") localStorage.removeItem(key);
        else localStorage.setItem(key, mode);
      } catch { /* An in-memory choice is enough when storage is unavailable. */ }
      apply();
    });
  }, { once: true });
})();
