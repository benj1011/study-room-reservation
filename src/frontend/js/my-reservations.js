function showBanner(message, type = "info") {
  const slot = document.getElementById("banner-slot");
  slot.innerHTML = `<div class="banner banner-${type}">${escapeHtml(message)}</div>`;
}

function stampClass(state) {
  if (state === "CONFIRMED") return "stamp-confirmed";
  if (state === "CANCELLED") return "stamp-cancelled";
  return "stamp-draft";
}

function formatDateTime(iso) {
  const value = new Date(iso);
  return {
    date: value.toLocaleDateString(),
    time: value.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };
}

function render(reservations) {
  const list = document.getElementById("list");

  if (!reservations.length) {
    list.innerHTML = `<div class="empty-state">You haven't reserved a room yet. <a href="index.html">Find one →</a></div>`;
    return;
  }

  list.innerHTML = reservations
    .map((r) => {
      const startInfo = formatDateTime(r.start_time);
      const endInfo = formatDateTime(r.end_time);
      const cancellable = r.state !== "CANCELLED";
      return `
      <div class="ticket" data-id="${r.id}">
        <div class="ticket-header">
          <div>
            <div class="room-code">${escapeHtml(r.room_name || "Room #" + r.room_id)}</div>
            <div class="meta-line">${startInfo.date} &nbsp;·&nbsp; ${startInfo.time} – ${endInfo.time}</div>
          </div>
          <span class="stamp ${stampClass(r.state)}">${r.state}</span>
        </div>
        <div class="ticket-body">
          <p class="helper-text" style="margin: 0 0 14px;">Purpose: ${escapeHtml(r.purpose || "—")}</p>
          <div class="actions-row">
            ${cancellable ? `<button class="btn-danger" data-cancel="${r.id}">Cancel</button>` : ""}
          </div>
        </div>
      </div>`;
    })
    .join("");

  list.querySelectorAll("[data-cancel]").forEach((btn) => {
    btn.addEventListener("click", () => handleCancel(Number(btn.dataset.cancel)));
  });
}

async function handleCancel(id) {
  try {
    await cancelReservation(id);
    await load();
  } catch (err) {
    showBanner(err.message || "Couldn't cancel that reservation.", "error");
  }
}

async function load() {
  const list = document.getElementById("list");
  list.innerHTML = `<p class="helper-text">Loading your reservations…</p>`;
  try {
    const reservations = await getMyReservations();
    render(reservations);
  } catch (err) {
    showBanner(err.message || "Couldn't load your reservations.", "error");
    list.innerHTML = "";
  }
}

load();
