const $ = (id) => document.getElementById(id);
const booleanText = (value, yes, no) => value ? yes : no;

function formatTimestamp(value) {
  if (!value) return 'Waiting';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function setCardState(id, active) {
  $(id).classList.toggle('is-active', Boolean(active));
}

function renderStatus(status) {
  $('temperature').textContent = Number(status.temperature ?? 0).toFixed(1);
  $('humidity').textContent = Number(status.humidity ?? 0).toFixed(0);
  $('human-radar').textContent = booleanText(status.human_radar, 'DETECTED', 'NO PRESENCE');
  $('human-camera').textContent = booleanText(status.human_camera, 'PERSON DETECTED', 'NO PERSON');
  $('camera-status').textContent = booleanText(status.camera_connected, 'CONNECTED', 'DISCONNECTED');
  $('fire-status').textContent = status.fire_level ?? 'NORMAL';
  $('buzzer').textContent = booleanText(status.buzzer, 'ON', 'OFF');
  $('wifi-status').textContent = booleanText(status.wifi_connected, 'CONNECTED', 'DISCONNECTED');
  $('ip-address').textContent = `IP: ${status.ip_address || 'N/A'}`;
  $('mqtt-status').textContent = booleanText(status.mqtt_connected, 'CONNECTED', 'DISCONNECTED');
  $('sensor-time').textContent = formatTimestamp(status.timestamp);
  $('assessment-message').textContent = status.message || 'Waiting for sensor data';

  const level = String(status.fire_level || 'NORMAL').toLowerCase();
  $('fire-level').textContent = status.fire_level || 'NORMAL';
  $('alert-panel').className = `alert-panel level-${level}`;
  $('fire-card').classList.remove('level-warning', 'level-emergency');
  if (level !== 'normal') $('fire-card').classList.add(`level-${level}`);
  setCardState('radar-card', status.human_radar);
  setCardState('camera-card', status.human_camera);
  setCardState('buzzer-card', status.buzzer);
  setCardState('wifi-card', status.wifi_connected);
  setCardState('mqtt-card', status.mqtt_connected);

  if (status.latency_ms === null || status.latency_ms === undefined) {
    $('latency').textContent = 'N/A';
    $('latency-unit').textContent = '';
  } else {
    $('latency').textContent = status.latency_ms;
    $('latency-unit').textContent = 'ms';
  }
}

async function refresh() {
  try {
    const [statusResponse, networkResponse] = await Promise.all([
      fetch('/api/status', { cache: 'no-store' }),
      fetch('/api/network', { cache: 'no-store' }),
    ]);
    if (!statusResponse.ok || !networkResponse.ok) throw new Error('Dashboard API unavailable');
    const status = await statusResponse.json();
    const network = await networkResponse.json();
    renderStatus({ ...status, ...network });
    $('poll-status').textContent = 'LIVE';
    $('poll-status').dataset.state = 'live';
  } catch {
    $('poll-status').textContent = 'API OFFLINE';
    $('poll-status').dataset.state = 'offline';
  }
}

async function refreshEvents() {
  try {
    const response = await fetch('/api/logs', { cache: 'no-store' });
    if (!response.ok) return;
    const events = await response.json();
    const list = $('event-list');
    list.replaceChildren();
    if (!events.length) {
      const empty = document.createElement('li');
      empty.className = 'empty-state';
      empty.textContent = 'No sensor events received yet.';
      list.append(empty);
      return;
    }
    for (const event of events.slice(0, 8)) {
      const item = document.createElement('li');
      const time = document.createElement('time');
      time.textContent = new Date(event.timestamp).toLocaleTimeString();
      const description = document.createElement('span');
      description.textContent = `${Number(event.temperature).toFixed(1)}°C · ${Number(event.humidity).toFixed(0)}% humidity · ${event.human_radar ? 'presence' : 'no presence'}`;
      const level = document.createElement('span');
      level.className = `event-level ${event.fire_level}`;
      level.textContent = event.fire_level || 'NORMAL';
      item.append(time, description, level);
      list.append(item);
    }
  } catch {
    // Event history is supplementary; live status continues polling.
  }
}

function tickClock() {
  $('clock').textContent = new Date().toLocaleTimeString();
}

refresh();
refreshEvents();
tickClock();
window.setInterval(refresh, 2000);
window.setInterval(refreshEvents, 10000);
window.setInterval(tickClock, 1000);
