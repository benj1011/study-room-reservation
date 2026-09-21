/* Shared API client. Times entered in the browser are sent as UTC instants.
   Requests always use PostgreSQL-backed API data; errors reach the page. */
const API_BASE = "http://127.0.0.1:8000";

// Demo identity only; authentication remains outside this integration.
const CURRENT_USER_ID = 1;
const CURRENT_USER_NAME = "You";

async function apiFetch(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
      signal: controller.signal,
    });
    const body = await res.json();
    if (!res.ok) {
      const detail = Array.isArray(body.detail)
        ? body.detail.map((item) => item.msg).join("; ")
        : body.detail;
      throw new Error(detail || `Request failed (${res.status})`);
    }
    return body;
  } finally {
    clearTimeout(timeout);
  }
}

function localDateTimeToISO(date, time) {
  return new Date(`${date}T${time}`).toISOString();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

async function getRooms() {
  return apiFetch("/rooms");
}

async function checkAvailability({ date, start, end, people }) {
  const qs = new URLSearchParams({
    start_time: localDateTimeToISO(date, start),
    end_time: localDateTimeToISO(date, end),
    people,
  });
  return apiFetch(`/rooms/available?${qs}`);
}

async function createReservation({ roomId, date, start, end, people, purpose }) {
  return apiFetch("/reservations", {
    method: "POST",
    body: JSON.stringify({
      user_id: CURRENT_USER_ID,
      room_id: roomId,
      start_time: localDateTimeToISO(date, start),
      end_time: localDateTimeToISO(date, end),
      number_of_people: Number(people),
      purpose,
    }),
  });
}

async function getMyReservations() {
  return apiFetch(`/reservations?user_id=${CURRENT_USER_ID}`);
}

async function getAllReservations() {
  return apiFetch("/reservations");
}

async function confirmReservation(id) {
  return apiFetch(`/reservations/${id}/confirm`, { method: "POST" });
}

async function cancelReservation(id) {
  return apiFetch(`/reservations/${id}/cancel`, { method: "POST" });
}
