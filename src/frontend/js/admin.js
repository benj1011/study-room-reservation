function showBanner(message, type = "info") {
  const slot = document.getElementById("banner-slot");
  slot.innerHTML = `<div class="banner banner-${type}">${message}</div>`;
}

function stampClass(state) {
  if (state === "CONFIRMED") return "stamp-confirmed";
  if (state === "CANCELLED") return "stamp-cancelled";
  return "stamp-draft";
}

function formatDateTime(iso) {
  const [datePart, timePart] = iso.split("T");
  const [y, m, d] = datePart.split("-");
  return { date: `${d}/${m}/${y}`, time: timePart.slice(0, 5) };
}

function render(reservations) {
  const list = document.getElementById("list");

  if (!reservations.length) {
    list.innerHTML = `<div class="empty-state">No reservations yet.</div>`;
    return;
  }

  // Pending first, so admins see what needs action.
  const sorted = [...reservations].sort((a, b) => {
    if (a.state === b.state) return 0;
    return a.state === "DRAFT" ? -1 : 1;
  });

  list.innerHTML = sorted
    .map((r) => {
      const startInfo = formatDateTime(r.start_time);
      const endInfo = formatDateTime(r.end_time);
      const isPending = r.state === "DRAFT";
      return `
      <div class="ticket" data-id="${r.id}">
        <div class="ticket-header">
          <div>
            <div class="room-code">Reservation #${r.id} &nbsp;·&nbsp; ${r.room_name || "Room #" + r.room_id}</div>
            <div class="meta-line">${startInfo.date} &nbsp;·&nbsp; ${startInfo.time} – ${endInfo.time} &nbsp;·&nbsp; ${r.number_of_people} people</div>
          </div>
          <span class="stamp ${stampClass(r.state)}">${r.state}</span>
        </div>
        <div class="ticket-body">
          <p class="helper-text" style="margin: 0 0 14px;">Purpose: ${r.purpose || "—"}</p>
          ${
            isPending
              ? `<div class="actions-row">
                   <button class="btn-danger" data-reject="${r.id}">Cancel</button>
                   <button class="btn-confirm" data-confirm="${r.id}">Confirm</button>
                 </div>`
              : ""
          }
        </div>
      </div>`;
    })
    .join("");

  list.querySelectorAll("[data-confirm]").forEach((btn) => {
    btn.addEventListener("click", () => handleConfirm(Number(btn.dataset.confirm)));
  });
  list.querySelectorAll("[data-reject]").forEach((btn) => {
    btn.addEventListener("click", () => handleReject(Number(btn.dataset.reject)));
  });
}

async function handleConfirm(id) {
  try {
    await confirmReservation(id);
    await load();
  } catch (err) {
    // Overlap rejection lands here — the backend (or the mock
    // standing in for it) enforces "no two confirmed overlaps".
    showBanner(err.message || "Couldn't confirm that reservation.", "error");
  }
}

async function handleReject(id) {
  try {
    await cancelReservation(id);
    await load();
  } catch (err) {
    showBanner(err.message || "Couldn't cancel that reservation.", "error");
  }
}

async function load() {
  const list = document.getElementById("list");
  list.innerHTML = `<p class="helper-text">Loading reservations…</p>`;
  try {
    const reservations = await getAllReservations();
    if (isUsingMockData()) {
      showBanner(
        "Backend not reachable yet — showing mock reservations for now.",
        "info"
      );
    }
    render(reservations);
  } catch (err) {
    showBanner(err.message || "Couldn't load reservations.", "error");
    list.innerHTML = "";
  }
}

load();
