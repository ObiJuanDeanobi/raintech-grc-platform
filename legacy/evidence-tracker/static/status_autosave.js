(function () {
  const form = document.querySelector("[data-autosave-status]");
  if (!form) {
    return;
  }

  const state = form.querySelector("[data-autosave-state]");
  const status = form.querySelector("select[name='status']");
  const notes = form.querySelector("textarea[name='notes']");
  let timer = null;
  let controller = null;

  function setState(message, kind) {
    if (!state) {
      return;
    }
    state.textContent = message;
    state.dataset.state = kind;
  }

  async function save() {
    if (controller) {
      controller.abort();
    }
    controller = new AbortController();
    setState("Saving...", "saving");

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        redirect: "manual",
        signal: controller.signal,
      });
      if (!response.ok && response.type !== "opaqueredirect") {
        throw new Error("Save failed");
      }
      setState("Saved", "saved");
    } catch (error) {
      if (error.name !== "AbortError") {
        setState("Could not save", "error");
      }
    }
  }

  function saveSoon() {
    window.clearTimeout(timer);
    setState("Unsaved changes", "pending");
    timer = window.setTimeout(save, 550);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    save();
  });

  if (status) {
    status.addEventListener("change", save);
  }

  if (notes) {
    notes.addEventListener("input", saveSoon);
    notes.addEventListener("blur", save);
  }
})();
