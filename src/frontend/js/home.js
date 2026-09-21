function showBanner(message, type = "info") {
  const slot = document.getElementById("banner-slot");
  slot.innerHTML = `<div class="banner banner-${type}">${escapeHtml(message)}</div>`;
}

function clearBanner() {
  document.getElementById("banner-slot").innerHTML = "";
}

function formatTimeRange(start, end) {
  return `${start} – ${end}`;
}

function renderRooms(rooms, { date, start, end, people }) {
  const container = document.getElementById("results");

  if (!rooms.length) {
    container.innerHTML = `
      <div class="empty-state">
        No rooms free for that time and party size. Try a shorter window or fewer people.
      </div>`;
    return;
  }

  container.innerHTML = rooms
    .map(
      (room) => `
      <div class="ticket">
        <div class="ticket-body">
          <div class="room-code">${escapeHtml(room.name)}</div>
          <div class="meta-line">Capacity: ${room.capacity} &nbsp;·&nbsp; Location: ${escapeHtml(room.location)}</div>
          <div class="actions-row" style="margin-top: 14px;">
            <a class="btn btn-confirm" href="create-reservation.html?room_id=${room.id}&room_name=${encodeURIComponent(
        room.name
      )}&location=${encodeURIComponent(room.location)}&capacity=${room.capacity}&date=${date}&start=${start}&end=${end}&people=${people}">
              Reserve
            </a>
          </div>
        </div>
      </div>`
    )
    .join("");
}

async function handleSearch(event) {
  event.preventDefault();
  clearBanner();

  const date = document.getElementById("date").value;
  const start = document.getElementById("start").value;
  const end = document.getElementById("end").value;
  const people = document.getElementById("people").value;

  if (end <= start) {
    showBanner("End time must be after start time.", "error");
    return;
  }

  const container = document.getElementById("results");
  container.innerHTML = `<p class="helper-text">Checking availability…</p>`;

  try {
    const rooms = await checkAvailability({ date, start, end, people });
    renderRooms(rooms, { date, start, end, people });
  } catch (err) {
    showBanner(err.message || "Something went wrong checking availability.", "error");
    container.innerHTML = "";
  }
}

function setDefaultDateTime() {
  const dateInput = document.getElementById("date");
  const startInput = document.getElementById("start");
  const endInput = document.getElementById("end");
  const today = new Date();
  today.setDate(today.getDate() + 1);
  dateInput.value = today.toISOString().slice(0, 10);
  startInput.value = "10:00";
  endInput.value = "12:00";
}

document.getElementById("search-form").addEventListener("submit", handleSearch);
setDefaultDateTime();
