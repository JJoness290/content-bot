// Lightweight interactions for copy buttons.
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-copy-target]");
  if (!button) return;
  const targetId = button.getAttribute("data-copy-target");
  const target = document.getElementById(targetId);
  if (!target) return;
  navigator.clipboard.writeText(target.textContent || "").then(() => {
    button.textContent = "Copied";
    setTimeout(() => {
      button.textContent = "Copy";
    }, 1500);
  });
});

const updateAutopilotStatus = async () => {
  const banner = document.getElementById("autopilot-banner");
  if (!banner) return;
  try {
    const response = await fetch("/api/autopilot/status");
    if (!response.ok) return;
    const data = await response.json();
    const lastRun = data.last_tick || "Never";
    const lastResult = data.last_run_result || "Unknown";
    document.getElementById("autopilot-last-run").textContent = lastRun;
    document.getElementById("autopilot-last-result").textContent = lastResult;
    if (data.enabled && (!data.last_tick || lastResult === "Skipped.")) {
      banner.classList.remove("hidden");
    } else if (data.enabled && data.last_tick) {
      const lastRunDate = new Date(data.last_tick);
      const minutes = data.interval_minutes || 15;
      const staleMs = minutes * 2 * 60 * 1000;
      if (Date.now() - lastRunDate.getTime() > staleMs) {
        banner.classList.remove("hidden");
      } else {
        banner.classList.add("hidden");
      }
    } else {
      banner.classList.add("hidden");
    }
  } catch (error) {
    banner.classList.remove("hidden");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  updateAutopilotStatus();
  setInterval(updateAutopilotStatus, 60000);
});

document.addEventListener("click", (event) => {
  const open = event.target.closest("[data-modal-open]");
  if (open) {
    const target = document.getElementById(open.dataset.modalOpen);
    if (target) {
      target.classList.remove("hidden");
      target.classList.add("flex");
    }
  }
  const close = event.target.closest("[data-modal-close]");
  if (close) {
    const target = document.getElementById(close.dataset.modalClose);
    if (target) {
      target.classList.add("hidden");
      target.classList.remove("flex");
    }
  }
});
