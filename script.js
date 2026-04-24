const $ = (id) => document.getElementById(id);

const desc = $("description");
const count = $("count");
const forgeBtn = $("generate");
const output = $("output");
const codeEl = $("code");
const scadLink = $("download-scad");
const stlLink = $("download-stl");
const stlNote = $("stl-note");
const copyBtn = $("copy");
const statusPanel = $("status-panel");
const statusText = $("status-text");
const errorPanel = $("error-panel");
const errorText = $("error-text");

const STATUS_LINES = [
  "parsing intent…",
  "picking tolerances…",
  "sketching primitives…",
  "booleans & fillets…",
  "verifying manifold…",
  "exporting…",
];

let statusTimer = null;

function showStatus() {
  errorPanel.hidden = true;
  statusPanel.hidden = false;
  let i = 0;
  statusText.textContent = STATUS_LINES[0];
  statusTimer = setInterval(() => {
    i = (i + 1) % STATUS_LINES.length;
    statusText.textContent = STATUS_LINES[i];
  }, 1400);
}

function hideStatus() {
  if (statusTimer) { clearInterval(statusTimer); statusTimer = null; }
  statusPanel.hidden = true;
}

function showError(msg) {
  hideStatus();
  errorText.textContent = msg;
  errorPanel.hidden = false;
}

desc.addEventListener("input", () => {
  count.textContent = desc.value.length;
});

forgeBtn.addEventListener("click", async () => {
  const description = desc.value.trim();
  if (!description) {
    showError("Write a description first.");
    return;
  }

  forgeBtn.disabled = true;
  output.hidden = true;
  showStatus();

  try {
    const res = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Something went wrong.");
      return;
    }

    codeEl.textContent = data.scad_code;
    scadLink.href = `/download/${encodeURIComponent(data.scad_filename)}`;
    scadLink.download = data.scad_filename;

    if (data.stl_filename) {
      stlLink.href = `/download/${encodeURIComponent(data.stl_filename)}`;
      stlLink.download = data.stl_filename;
      stlLink.hidden = false;
      stlNote.hidden = true;
    } else {
      stlLink.hidden = true;
      if (data.stl_message) {
        stlNote.textContent = data.stl_message + "\nYou can open the .scad file in OpenSCAD and export STL manually.";
        stlNote.hidden = false;
      } else {
        stlNote.hidden = true;
      }
    }

    hideStatus();
    output.hidden = false;
    output.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    showError(String(err));
  } finally {
    forgeBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(codeEl.textContent);
    const original = copyBtn.textContent;
    copyBtn.textContent = "copied";
    setTimeout(() => (copyBtn.textContent = original), 1200);
  } catch {
    showError("Could not access clipboard.");
  }
});

// keyboard: Ctrl/Cmd+Enter to forge
desc.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    forgeBtn.click();
  }
});
