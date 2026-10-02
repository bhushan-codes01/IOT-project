const $ = (id) => document.getElementById(id);
const setText = (id, value) => { $(id).textContent = value; };
let soundEnabled = false;
let buzzerActive = false;
let alarmInterval = null;
let alarmAudio = null;
let alarmGain = null;

function booleanText(value, yes, no) {
  return value ? yes : no;
}

function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function formatTimestamp(value, timeOnly = false) {
  if (!value) return 'WAITING';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return timeOnly ? date.toLocaleTimeString() : date.toLocaleString();
}

function setStateClass(element, baseClass, state) {
  element.className = `${baseClass} ${state}`.trim();
}

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
    alarmGain.gain.linearRampToValueAtTime(0.24, now + 0.015);
    alarmGain.gain.setValueAtTime(0.24, now + 0.14);
    alarmGain.gain.linearRampToValueAtTime(0, now + 0.19);
  };
  beep();
  alarmInterval = window.setInterval(beep, 900);
}

function setCardState(cardId, level) {
  const card = $(cardId);
  card.classList.remove('normal-card', 'red-card', 'amber-card', 'blue-card');
  card.classList.add(level === 'EMERGENCY' ? 'red-card' : level === 'WARNING' ? 'amber-card' : 'normal-card');
}

function setValueTone(id, level) {
  const value = $(id);
  value.classList.remove('green', 'red', 'amber', 'blue');
  value.classList.add(level === 'EMERGENCY' ? 'red' : level === 'WARNING' ? 'amber' : 'green');
}

function createMarker(type, symbol, label, left, top) {
  const marker = document.createElement('div');
  marker.className = `map-marker ${type}`;
  marker.style.left = `${left}%`;
  marker.style.top = `${top}%`;
  const dot = document.createElement('span');
  dot.className = 'map-marker-dot';
  dot.textContent = symbol;
  const text = document.createElement('span');
  text.className = 'map-marker-label';
  text.textContent = label;
  marker.append(dot, text);
  return marker;
}

function renderMap(status, level) {
  const markers = $('map-markers');
  markers.replaceChildren();

  const espOnline = Boolean(status.esp32_connected);
  const presence = Boolean(status.sensor_connected && status.human_radar);
  const distance = finiteNumber(status.human_distance_cm, NaN);
  const hasDistance = presence && Number.isFinite(distance) && distance > 0;
  const zone = hasDistance ? (distance >= 400 ? 'FAR' : distance >= 150 ? 'MID' : 'NEAR') : '';
  const markerTop = zone === 'FAR' ? 16.7 : zone === 'NEAR' ? 83.3 : 50;

  $('map-container').dataset.level = level;
  const radarConnected = status.radar_connected;
  const radarState = radarConnected === null || radarConnected === undefined
    ? 'UNKNOWN'
    : radarConnected ? (presence ? 'HUMAN DETECTED' : 'CLEAR') : 'DISCONNECTED';
  setText('map-radar-status', `RADAR: ${radarState}`);
  $('map-radar-status').className = `map-radar-status ${presence ? 'detected' : radarConnected === false ? 'disconnected' : 'unknown'}`;

  markers.append(createMarker('esp', 'E', 'ESP32 / LD2410C', 50, 83.3));
  if (level !== 'NORMAL') {
    markers.append(createMarker('fire', '!', 'HIGH TEMP', 15, 16.7));
  }
  if (presence) {
    markers.append(createMarker('human', '•', 'HUMAN', 61, markerTop));
  }

  setText('range-val', hasDistance ? `${Math.round(distance)} CM · ${zone} BAND` : presence ? 'RANGE UNAVAILABLE' : 'NO TARGET');
  const espStatus = $('esp-status-cell').querySelector('strong');
  espStatus.textContent = espOnline ? 'ONLINE' : 'OFFLINE';
  espStatus.className = espOnline ? 'connected' : 'disconnected';
  const hasPublisher = status.sensor_device && status.sensor_device !== 'UNKNOWN';
  const lastSeen = hasPublisher ? formatTimestamp(status.last_seen, true) : 'WAITING';
  setText('last-seen', hasPublisher && !status.sensor_connected ? `OFFLINE · ${lastSeen}` : lastSeen);
}

function renderStatus(status, network) {
  const temperature = finiteNumber(status.temperature);
  const humidity = finiteNumber(status.humidity);
  const level = ['NORMAL', 'WARNING', 'EMERGENCY'].includes(status.fire_level) ? status.fire_level : 'NORMAL';
  const radarPresent = Boolean(status.sensor_connected && status.human_radar);
  const cameraPresent = Boolean(status.human_camera);
  const buzzer = Boolean(status.buzzer);

  $('temp-val').replaceChildren(document.createTextNode(temperature.toFixed(1)), Object.assign(document.createElement('small'), { textContent: ' °C' }));
  $('hum-val').replaceChildren(document.createTextNode(String(Math.round(humidity))), Object.assign(document.createElement('small'), { textContent: ' %' }));
  $('temp-bar').style.width = `${clamp(temperature, 0, 100)}%`;
  $('hum-bar').style.width = `${clamp(humidity, 0, 100)}%`;

  setCardState('temp-card', level);
  setValueTone('temp-val', level);
  $('temp-bar').className = `sc-fill ${level === 'EMERGENCY' ? 'red' : level === 'WARNING' ? 'amber' : 'green'}`;
  $('temp-sub').className = `sc-sub ${level === 'EMERGENCY' ? 'red' : level === 'WARNING' ? 'amber' : 'green'}`;
  setText('temp-sub', level === 'NORMAL' ? 'Ambient sensor reading' : `${level} THRESHOLD`);

  setCardState('radar-card', radarPresent ? 'EMERGENCY' : 'NORMAL');
  setValueTone('radar-val', radarPresent ? 'EMERGENCY' : 'NORMAL');
  setText('radar-val', radarPresent ? 'HUMAN DETECTED' : 'NO PRESENCE');
  $('radar-badge').className = `sc-badge ${radarPresent ? 'r' : 'g'}`;
  $('presence-dot').classList.toggle('detected', radarPresent);
  setText('presence-label', radarPresent ? 'TARGET DETECTED' : status.radar_connected === false ? 'RADAR OFFLINE' : 'NO TARGET DETECTED');

  setCardState('cam-card', cameraPresent ? 'EMERGENCY' : 'NORMAL');
  setValueTone('cam-val', cameraPresent ? 'EMERGENCY' : 'NORMAL');
  setText('cam-val', cameraPresent ? 'PERSON DETECTED' : 'NO PERSON');
  $('cam-badge').className = `sc-badge ${cameraPresent ? 'r' : 'g'}`;
  setText('cam-status', booleanText(status.camera_connected, 'CONNECTED', 'DISCONNECTED'));
  $('cam-status').className = status.camera_connected ? 'connected' : 'unknown';

  setCardState('fire-card', level);
  setValueTone('fire-val', level);
  setText('fire-val', level);
  $('fire-badge').className = `sc-badge ${level === 'EMERGENCY' ? 'r' : level === 'WARNING' ? 'a' : 'g'}`;

  setCardState('buz-card', buzzer ? 'EMERGENCY' : 'NORMAL');
  setValueTone('buz-val', buzzer ? 'EMERGENCY' : 'NORMAL');
  setText('buz-val', buzzer ? 'ACTIVE' : 'OFF');
  $('buz-badge').className = `sc-badge ${buzzer ? 'r' : 'g'}`;

  const statusElement = $('system-status');
  statusElement.className = `status-val ${level.toLowerCase()}`;
  setText('system-status', level);
  setText('status-sub', status.message || 'Waiting for sensor data');
  const hasPublisher = status.sensor_device && status.sensor_device !== 'UNKNOWN';
  setText('sensor-time', hasPublisher ? formatTimestamp(status.last_seen || status.timestamp) : 'WAITING');
  setText('last-update', status.sensor_connected && status.last_seen
    ? `UPDATED ${formatTimestamp(status.last_seen, true)}`
    : hasPublisher ? 'SENSOR OFFLINE' : 'WAITING FOR SENSOR');

  const wifi = Boolean(network.wifi_connected);
  const mqtt = Boolean(status.mqtt_connected);
  $('wifi-val').className = `cc-value ${wifi ? 'connected' : 'disconnected'}`;
  setText('wifi-val', booleanText(wifi, 'CONNECTED', 'DISCONNECTED'));
  $('wifi-ip').className = `cc-sub ${wifi ? 'connected' : 'unknown'}`;
  setText('wifi-ip', `IP: ${network.ip_address || 'N/A'}`);
  $('mqtt-val').className = `cc-value ${mqtt ? 'connected' : 'disconnected'}`;
  setText('mqtt-val', booleanText(mqtt, 'CONNECTED', 'DISCONNECTED'));
  setText('latency-val', network.latency_ms === null || network.latency_ms === undefined ? 'N/A' : `${network.latency_ms} MS`);

  const liveLabel = status.demo_mode ? 'DEMO LIVE' : 'LIVE';
  setText('poll-status', liveLabel);
  $('live-dot').className = `dot ${level === 'EMERGENCY' ? 'red' : level === 'WARNING' ? 'amber' : ''}`.trim();
  setText('decision-text', status.demo_mode
    ? 'Demo readings are simulated and do not come from physical sensors.'
    : 'Temperature thresholds set the warning and emergency state. Radar presence is reported independently. This prototype is not a certified alarm.');

  buzzerActive = buzzer;
  updateAlarmSound();
  renderMap(status, level);
}

function renderEvents(events) {
  const list = $('events-list');
  list.replaceChildren();
  if (!Array.isArray(events) || events.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'event-empty';
    empty.textContent = 'No sensor events received yet.';
    list.append(empty);
    return;
  }

  for (const event of events.slice(0, 8)) {
    const item = document.createElement('li');
    item.className = 'event-row';
    const time = document.createElement('time');
    time.className = 'event-time';
    time.textContent = formatTimestamp(event.timestamp, true);
    const message = document.createElement('span');
    const level = ['WARNING', 'EMERGENCY'].includes(event.fire_level) ? event.fire_level : 'NORMAL';
    message.className = `event-msg ${level === 'EMERGENCY' ? 'red' : level === 'WARNING' ? 'amber' : 'green'}`;
    message.textContent = `${finiteNumber(event.temperature).toFixed(1)} C · ${Math.round(finiteNumber(event.humidity))}% RH · ${event.human_radar ? 'human detected' : 'no target'} · ${level}`;
    item.append(time, message);
    list.append(item);
  }
}

async function refresh() {
  try {
    const [statusResponse, networkResponse] = await Promise.all([
      fetch('/api/status', { cache: 'no-store' }),
      fetch('/api/network', { cache: 'no-store' }),
    ]);
    if (!statusResponse.ok || !networkResponse.ok) throw new Error('Dashboard API unavailable');
    const [status, network] = await Promise.all([statusResponse.json(), networkResponse.json()]);
    renderStatus(status, network);
  } catch {
    setText('poll-status', 'APP OFFLINE');
    $('live-dot').className = 'dot amber';
    $('system-status').className = 'status-val warning';
    setText('system-status', 'OFFLINE');
    setText('status-sub', 'Cannot reach Flask backend');
  }
}

async function refreshEvents() {
  try {
    const response = await fetch('/api/logs', { cache: 'no-store' });
    if (response.ok) renderEvents(await response.json());
  } catch {
    // Event history is supplementary; live status continues polling.
  }
}

function tickClock() {
  setText('clock', new Date().toLocaleTimeString());
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
  button.title = soundEnabled ? 'Disable browser alarm sound' : 'Enable browser alarm sound';
  updateAlarmSound();
});
