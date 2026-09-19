function showBanner(message, type = "info") {
  const slot = document.getElementById("banner-slot");
  slot.innerHTML = `<div class="banner banner-${type}">${message}</div>`;
}

const params = new URLSearchParams(window.location.search);

const roomId = Number(params.get("room_id")) || 1;
const roomName = params.get("room_name") || "A101";
const location = params.get("location") || "Building A";
const capacity = Number(params.get("capacity")) || 10;
const date = params.get("date") || new Date().toISOString().slice(0, 10);
const start = params.get("start") || "10:00";
const end = params.get("end") || "12:00";
const defaultPeople = params.get("people") || "";

document.getElementById("summary-room").textContent = roomName;
document.getElementById("summary-location").textContent = `${location} · Capacity ${capacity}`;
document.getElementById("summary-date").textContent = date;
document.getElementById("summary-time").textContent = `${start} – ${end}`;
document.getElementById("capacity-hint").textContent = `This room holds up to ${capacity} people.`;

const peopleInput = document.getElementById("people");
peopleInput.max = capacity;
if (defaultPeople) peopleInput.value = defaultPeople;

document.getElementById("reservation-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const people = Number(peopleInput.value);
  const purpose = document.getElementById("purpose").value.trim();
  const submitBtn = document.getElementById("submit-btn");

  if (people > capacity) {
    showBanner(
      `${people} people won't fit — ${roomName} holds a maximum of ${capacity}.`,
      "error"
    );
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Creating…";

  try {
    const reservation = await createReservation({
      roomId,
      roomName,
      date,
      start,
      end,
      people,
      purpose,
    });

    const modeNote = isUsingMockData()
      ? " (saved to mock data — backend isn't reachable yet)"
      : "";

    showBanner(
      `Reservation created: #${reservation.id}, status ${reservation.state}${modeNote}.`,
      "success"
    );

    submitBtn.textContent = "Created ✓";
    setTimeout(() => {
      window.location.href = "my-reservations.html";
    }, 900);
  } catch (err) {
    showBanner(err.message || "Couldn't create the reservation. Try again.", "error");
    submitBtn.disabled = false;
    submitBtn.textContent = "Create Reservation";
  }
});
