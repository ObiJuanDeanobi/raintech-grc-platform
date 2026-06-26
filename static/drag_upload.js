(function () {
  const zones = document.querySelectorAll("[data-drop-upload]");

  function filenameStem(name) {
    return name.replace(/\.[^.]+$/, "") || name;
  }

  function setStatus(zone, message) {
    const status = zone.querySelector("[data-drop-status]");
    if (status) {
      status.textContent = message;
    }
  }

  async function uploadFiles(zone, files) {
    const uploadUrl = zone.dataset.uploadUrl;
    const fileList = Array.from(files || []).filter((file) => file && file.size >= 0);
    if (!uploadUrl || fileList.length === 0) {
      return;
    }

    zone.classList.add("is-uploading");
    setStatus(zone, `Uploading ${fileList.length} file${fileList.length === 1 ? "" : "s"}...`);

    for (let index = 0; index < fileList.length; index += 1) {
      const file = fileList[index];
      const formData = new FormData();
      formData.append("evidence_file", file, file.name);
      formData.append("title", filenameStem(file.name));
      formData.append("source", "Dropped from Windows Explorer");
      formData.append("notes", "");

      setStatus(zone, `Uploading ${index + 1} of ${fileList.length}: ${file.name}`);
      const response = await fetch(uploadUrl, {
        method: "POST",
        body: formData,
        redirect: "manual",
      });

      if (!response.ok && response.type !== "opaqueredirect") {
        zone.classList.remove("is-uploading");
        zone.classList.add("has-error");
        setStatus(zone, `Upload failed for ${file.name}.`);
        return;
      }
    }

    setStatus(zone, "Upload complete. Refreshing evidence list...");
    window.location.reload();
  }

  zones.forEach((zone) => {
    const input = zone.querySelector("[data-drop-file-input]");

    zone.addEventListener("click", () => {
      if (input) {
        input.click();
      }
    });

    zone.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === " ") && input) {
        event.preventDefault();
        input.click();
      }
    });

    zone.addEventListener("dragenter", (event) => {
      event.preventDefault();
      zone.classList.add("is-dragging");
    });

    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
      zone.classList.add("is-dragging");
    });

    zone.addEventListener("dragleave", (event) => {
      if (!zone.contains(event.relatedTarget)) {
        zone.classList.remove("is-dragging");
      }
    });

    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      zone.classList.remove("is-dragging");
      uploadFiles(zone, event.dataTransfer.files).catch(() => {
        zone.classList.remove("is-uploading");
        zone.classList.add("has-error");
        setStatus(zone, "Upload failed. Please try again.");
      });
    });

    if (input) {
      input.addEventListener("change", () => {
        uploadFiles(zone, input.files).catch(() => {
          zone.classList.remove("is-uploading");
          zone.classList.add("has-error");
          setStatus(zone, "Upload failed. Please try again.");
        });
      });
    }
  });
})();
