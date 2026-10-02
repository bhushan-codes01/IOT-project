const $ = (id) => document.getElementById(id);
const booleanText = (value, yes, no) => value ? yes : no;
let soundEnabled = false;
let buzzerActive = false;
let alarmInterval = null;
let alarmAudio = null;
let alarmGain = null;

function updateAlarmSound() {
  if (!soundEnabled || !buzzerActive || !alarmAudio || !alarmGain) {
    if (alarmInterval !== null) window.clearInterval(alarmInterval);
    alarmInterval = null;
    if (alarmGain && alarmAudio) alarmGain.gain.setTargetAtTime(0, alarmAudio.currentTime, 0.02);
    return;
  }
  if (alarmInterval !== null) return;

  const beep = () => {
    const now = alarmAudio.currentTime;
    alarmGain.gain.cancelScheduledValues(now);
    alarmGain.gain.setValueAtTime(0, now);
    alarmGain.gain.linearRampToValueAtTime(0.32, now + 0.015);
    alarmGain.gain.setValueAtTime(0.32, now + 0.16);
    alarmGain.gain.linearRampToValueAtTime(0, now + 0.2);
  };
  beep();
  alarmInterval = window.setInterval(beep, 900);
}

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
  renderMap(status);
  buzzerActive = Boolean(status.buzzer);
  updateAlarmSound();

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

function renderMap(status) {
  const map = $('environment-map');
  const sensorConnected = Boolean(status.sensor_connected);
  const presence = sensorConnected && Boolean(status.human_radar);
  const distance = Number(status.human_distance_cm);
  const hasDistance = presence && Number.isFinite(distance) && distance > 0;
  const zone = hasDistance ? (distance < 150 ? 'near' : distance < 400 ? 'mid' : 'far') : 'unknown';
  const radarStatus = status.radar_connected === null || status.radar_connected === undefined
    ? 'UNKNOWN'
    : booleanText(status.radar_connected, 'CONNECTED', 'DISCONNECTED');

  map.dataset.zone = zone;
  map.dataset.presence = String(presence);
  map.dataset.level = status.fire_level || 'NORMAL';
  $('map-radar-status').textContent = `RADAR ${radarStatus}`;
  $('map-person').hidden = !presence;
  $('map-person-label').textContent = hasDistance
    ? `HUMAN · ${zone.toUpperCase()} · ${Math.round(distance)} CM`
    : 'HUMAN DETECTED · RANGE UNAVAILABLE';
  $('map-range').textContent = hasDistance
    ? `RANGE: ${Math.round(distance)} CM · ${zone.toUpperCase()} BAND`
    : presence ? 'RANGE: UNAVAILABLE' : 'RANGE: NO TARGET';

  const source = status.sensor_device || 'SENSOR';
  $('device-status').textContent = `${source}: ${sensorConnected ? 'ONLINE' : 'OFFLINE'}`;
  $('device-seen').textContent = `LAST SEEN: ${formatTimestamp(status.last_seen)}`;
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
    $('poll-status').textContent = status.demo_mode ? 'DEMO LIVE' : 'LIVE';
    $('poll-status').dataset.state = status.demo_mode ? 'demo' : 'live';
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

$('sound-toggle').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  if (soundEnabled) {
    soundEnabled = false;
  } else {
    const AudioContextType = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextType) {
      button.textContent = 'SOUND N/A';
      button.disabled = true;
      return;
    }
    try {
      alarmAudio = alarmAudio || new AudioContextType();
      await alarmAudio.resume();
      if (!alarmGain) {
        const oscillator = alarmAudio.createOscillator();
        alarmGain = alarmAudio.createGain();
        oscillator.type = 'square';
        oscillator.frequency.value = 880;
        alarmGain.gain.value = 0;
        oscillator.connect(alarmGain);
        alarmGain.connect(alarmAudio.destination);
        oscillator.start();
      }
      soundEnabled = true;
    } catch {
      button.textContent = 'SOUND N/A';
      return;
    }
  }
  button.textContent = soundEnabled ? 'SOUND ON' : 'SOUND OFF';
  button.setAttribute('aria-pressed', String(soundEnabled));
  button.title = soundEnabled ? 'Disable browser buzzer sound' : 'Enable browser buzzer sound';
  updateAlarmSound();
});
