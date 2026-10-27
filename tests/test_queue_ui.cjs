// Run with: node --test tests/test_queue_ui.cjs
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function screen(responses, consent = false) {
  const elements = new Map();
  const calls = [], dialogs = [];
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: id === 'people' ? '2' : id === 'purpose' ? 'Study' : '',
      textContent: '', innerHTML: '', disabled: false, children: [],
      appendChild(child) { this.children.push(child); },
      addEventListener(event, handler) { this[event] = handler; },
      querySelectorAll() { return []; },
    });
    return elements.get(id);
  }
  const context = vm.createContext({
    URLSearchParams, AbortController, setTimeout, clearTimeout,
    setInterval() {}, console,
    window: {
      location: { search: '?room_id=1&date=2030-10-01&start=10:00&end=11:00', href: '' },
      confirm(message) { dialogs.push(message); return consent; },
    },
    document: { getElementById: element, createElement: () => ({}), hidden: false },
    fetch: async (url, options) => {
      calls.push({ url, body: options.body && JSON.parse(options.body) });
      const response = responses.shift();
      assert.ok(response, 'Unexpected API request');
      return { ok: response.status < 400, status: response.status, json: async () => response.body };
    },
  });
  const load = name => vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/frontend/js', name), 'utf8'), context);
  load('api.js');
  return { load, context, element, calls, dialogs };
}
const warning = () => ({ status: 409, body: { detail: { code: 'QUEUE_REQUIRED', message: 'Another request exists.' } } });
const booked = () => ({ status: 409, body: { detail: { code: 'ROOM_BOOKED', message: 'Room already booked. Choose another time.' } } });
const submit = ui => ui.element('reservation-form').submit({ preventDefault() {} });

test('declining queue consent does not send a second create', async () => {
  const ui = screen([warning()], false); ui.load('create-reservation.js'); await submit(ui);
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.calls[0].body.join_queue, false);
  assert.match(ui.dialogs[0], /cancelled if an earlier request is confirmed/);
  assert.equal(ui.element('submit-btn').disabled, false);
  assert.match(ui.element('banner-slot').innerHTML, /Not submitted/);
});

test('accepting sends explicit consent and leaves the warning visible', async () => {
  const ui = screen([warning(), { status: 201, body: { id: 2, state: 'DRAFT', queue_status: 'WAITING' } }], true);
  ui.load('create-reservation.js'); await submit(ui);
  assert.equal(ui.calls.length, 2);
  assert.equal(ui.calls[1].body.join_queue, true);
  assert.match(ui.calls[1].url, /:5000\/reservations$/);
  assert.match(ui.element('banner-slot').innerHTML, /Auto-cancelled/);
  assert.equal(ui.context.window.location.href, '');
  assert.equal(ui.element('banner-slot').children[0].href, 'my-reservations.html');
});

test('a booking confirmed during the dialog rejects the retry', async () => {
  const ui = screen([warning(), booked()], true); ui.load('create-reservation.js'); await submit(ui);
  assert.match(ui.element('banner-slot').innerHTML, /Room already booked/);
  assert.equal(ui.element('submit-btn').disabled, false);
  assert.equal(ui.element('banner-slot').children.length, 0);
});

test('already confirmed room does not offer a queue', async () => {
  const ui = screen([booked()]); ui.load('create-reservation.js'); await submit(ui);
  assert.equal(ui.dialogs.length, 0);
  assert.match(ui.element('banner-slot').innerHTML, /Choose another time/);
});

test('successful first request displays pending confirmation', async () => {
  const ui = screen([{ status: 201, body: { id: 1, state: 'DRAFT', queue_status: 'READY' } }]);
  ui.load('create-reservation.js'); await submit(ui);
  assert.equal(ui.dialogs.length, 0);
  assert.match(ui.element('banner-slot').innerHTML, /Room not reserved yet/);
});

test('cancellation and waiting messages are rendered in My Reservations', async () => {
  const ui = screen([{ status: 200, body: [] }]); ui.load('my-reservations.js');
  await new Promise(resolve => setImmediate(resolve));
  vm.runInContext(`render([
    {id: 1, room_id: 1, state: 'CANCELLED', cancellation_reason: 'Another request confirmed.', start_time: '2030-10-01T10:00:00Z', end_time: '2030-10-01T11:00:00Z'},
    {id: 2, room_id: 1, state: 'DRAFT', queue_status: 'WAITING', start_time: '2030-10-02T10:00:00Z', end_time: '2030-10-02T11:00:00Z'}
  ])`, ui.context);
  assert.match(ui.element('list').innerHTML, /Another request confirmed/);
  assert.match(ui.element('list').innerHTML, /WAITING/);
  assert.match(ui.element('list').innerHTML, /Auto-cancelled/);
});

test('admin cannot click Confirm for a waiting request', async () => {
  const ui = screen([{ status: 200, body: [] }]); ui.load('admin.js');
  await new Promise(resolve => setImmediate(resolve));
  vm.runInContext(`render([{id: 2, room_id: 1, state: 'DRAFT', queue_status: 'WAITING', number_of_people: 2, start_time: '2030-10-01T10:00:00Z', end_time: '2030-10-01T11:00:00Z'}])`, ui.context);
  assert.match(ui.element('list').innerHTML, /data-confirm="2" disabled/);
  assert.match(ui.element('list').innerHTML, /WAITING/);
});
