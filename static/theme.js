(function () {
  const button = document.querySelector("[data-theme-toggle]");
  const label = document.querySelector("[data-theme-label]");
  const icon = document.querySelector("[data-theme-icon]");

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("cmmc-theme", theme);
    if (label) {
      label.textContent = theme === "dark" ? "Dark" : "Light";
    }
    if (icon) {
      icon.textContent = theme === "dark" ? "☾" : "☼";
    }
    if (button) {
      button.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} mode`);
      button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    }
  }

  applyTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");

  if (button) {
    button.addEventListener("click", () => {
      applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
    });
  }
})();
