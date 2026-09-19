/* ============================================================
   Study Room Reservation — API layer
   ------------------------------------------------------------
   Matches the contract agreed with the backend team:

     GET  /rooms
     GET  /rooms/available?date=...&start=...&end=...&people=...
     POST /reservations
     GET  /reservations?user_id=...
     GET  /reservations            (admin: all reservations)
     POST /reservations/{id}/confirm
     POST /reservations/{id}/cancel

   While the backend isn't running yet (or is unreachable), every
   function below silently falls back to mock data held in memory,
   so you can build and demo the whole frontend on your own.
   Once Person 1's backend is up on localhost:8000, this file
   starts talking to it automatically — no changes needed.
   ============================================================ */

const API_BASE = "http://localhost:8000";

// Per the project's assumption, we treat the user as already
// authenticated. Hardcode a demo user until real auth exists.
const CURRENT_USER_ID = 1;
const CURRENT_USER_NAME = "You";

/* ---------- low-level fetch helper ---------- */

async function apiFetch(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
    clearTimeout(timeout);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return await res.json();
  } catch (err) {
    clearTimeout(timeout);
    throw err;
  }
}

/* ---------- mock data (used until the backend is reachable) ---------- */

const mockRooms = [
  { id: 1, name: "A101", location: "Building A", capacity: 10 },
  { id: 2, name: "B203", location: "Building B", capacity: 20 },
  { id: 3, name: "C310", location: "Building C", capacity: 4 },
];

let mockReservations = [
  {
    id: 123,
    user_id: 1,
    room_id: 1,
    room_name: "A101",
    start_time: "2026-09-20T10:00:00",
    end_time: "2026-09-20T12:00:00",
    number_of_people: 6,
    purpose: "Team meeting",
    state: "DRAFT",
  },
  {
    id: 124,
    user_id: 1,
    room_id: 2,
    room_name: "B203",
    start_time: "2026-09-22T14:00:00",
    end_time: "2026-09-22T15:00:00",
    number_of_people: 12,
    purpose: "Project discussion",
    state: "CONFIRMED",
  },
];

let nextMockId = 125;

/* Lets the UI show a small "demo mode" banner when we're on mock data. */
let usingMockData = false;
function isUsingMockData() {
  return usingMockData;
}

/* ---------- public API ---------- */

async function getRooms() {
  try {
    const data = await apiFetch(`/rooms`);
    usingMockData = false;
    return data;
  } catch (err) {
    usingMockData = true;
    return mockRooms;
  }
}

async function checkAvailability({ date, start, end, people }) {
  const qs = new URLSearchParams({ date, start, end, people }).toString();
  try {
    const data = await apiFetch(`/rooms/available?${qs}`);
    usingMockData = false;
    return data;
  } catch (err) {
    usingMockData = true;
    const minPeople = Number(people) || 0;
    return mockRooms.filter((r) => r.capacity >= minPeople);
  }
}

async function createReservation({ roomId, roomName, date, start, end, people, purpose }) {
  const payload = {
    user_id: CURRENT_USER_ID,
    room_id: roomId,
    start_time: `${date}T${start}:00`,
    end_time: `${date}T${end}:00`,
    number_of_people: Number(people),
    purpose: purpose,
  };

  try {
    const data = await apiFetch(`/reservations`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    usingMockData = false;
    return data;
  } catch (err) {
    usingMockData = true;
    const reservation = {
      id: nextMockId++,
      ...payload,
      room_name: roomName,
      state: "DRAFT",
    };
    mockReservations.push(reservation);
    return reservation;
  }
}

async function getMyReservations() {
  try {
    const data = await apiFetch(`/reservations?user_id=${CURRENT_USER_ID}`);
    usingMockData = false;
    return data;
  } catch (err) {
    usingMockData = true;
    return mockReservations.filter((r) => r.user_id === CURRENT_USER_ID);
  }
}

async function getAllReservations() {
  try {
    const data = await apiFetch(`/reservations`);
    usingMockData = false;
    return data;
  } catch (err) {
    usingMockData = true;
    return mockReservations;
  }
}

async function confirmReservation(id) {
  try {
    const data = await apiFetch(`/reservations/${id}/confirm`, { method: "POST" });
    usingMockData = false;
    return data;
  } catch (err) {
    usingMockData = true;
    const r = mockReservations.find((r) => r.id === id);
    if (!r) throw new Error("Reservation not found");

    // Mirror the backend's overlap rule locally so the mock behaves
    // the same way the real endpoint eventually will.
    const overlap = mockReservations.some(
      (other) =>
        other.id !== id &&
        other.room_id === r.room_id &&
        other.state === "CONFIRMED" &&
        new Date(other.start_time) < new Date(r.end_time) &&
        new Date(r.start_time) < new Date(other.end_time)
    );
    if (overlap) {
      throw new Error("Another confirmed reservation overlaps this room and time.");
    }
    r.state = "CONFIRMED";
    return r;
  }
}

async function cancelReservation(id) {
  try {
    const data = await apiFetch(`/reservations/${id}/cancel`, { method: "POST" });
    usingMockData = false;
    return data;
  } catch (err) {
    usingMockData = true;
    const r = mockReservations.find((r) => r.id === id);
    if (!r) throw new Error("Reservation not found");
    r.state = "CANCELLED";
    return r;
  }
}
