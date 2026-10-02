const $ = (id) => document.getElementById(id);
const setText = (id, value) => { $(id).textContent = value; };
let soundEnabled = false;
let buzzerActive = false;
let alarmInterval = null;
let alarmAudio = null;
let alarmGain = null;
let cameraBaseUrl = '';
let cameraStreamActive = false;
let cameraRefreshTimer = null;
let cameraRefreshSeconds = 5;
const MAP_MAX_RANGE_CM = 600;

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

function renderMap(status, level) {
  window.lastRadarStatus = status;
  window.lastRadarLevel = level;
  const canvas = $('radar-map');
  const context = canvas.getContext('2d');
  if (!context) return;
  const bounds = canvas.getBoundingClientRect();
  if (!bounds.width || !bounds.height) return;
  const pixelRatio = Math.max(1, window.devicePixelRatio || 1);
  canvas.width = Math.round(bounds.width * pixelRatio);
  canvas.height = Math.round(bounds.height * pixelRatio);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

  const width = bounds.width;
  const height = bounds.height;
  const espOnline = Boolean(status.esp32_connected);
  const presence = Boolean(status.sensor_connected && status.human_radar);
  const distance = finiteNumber(status.human_distance_cm, NaN);
  const hasDistance = presence && Number.isFinite(distance) && distance > 0;
  const zone = hasDistance ? (distance >= 400 ? 'FAR' : distance >= 150 ? 'MID' : 'NEAR') : '';
  const centerX = width / 2;
  const centerY = height / 2 + 8;
  const radius = Math.max(30, Math.min(width * 0.42, height / 2 - 22));
  const scale = radius / MAP_MAX_RANGE_CM;
  const ringColor = level === 'EMERGENCY' ? '#ff5757' : level === 'WARNING' ? '#ffad42' : '#54f078';

  $('map-container').dataset.level = level;
  const radarConnected = status.radar_connected;
  const radarState = radarConnected === null || radarConnected === undefined
    ? 'UNKNOWN'
    : radarConnected ? (presence ? 'HUMAN DETECTED' : 'CLEAR') : 'DISCONNECTED';
  setText('map-radar-status', `RADAR: ${radarState}`);
  $('map-radar-status').className = `map-radar-status ${presence ? 'detected' : radarConnected === false ? 'disconnected' : 'unknown'}`;

  context.clearRect(0, 0, width, height);
  context.fillStyle = '#050a06';
  context.fillRect(0, 0, width, height);
  context.strokeStyle = 'rgba(84, 240, 120, 0.08)';
  context.lineWidth = 1;
  for (let x = 0; x <= width; x += 32) {
    context.beginPath(); context.moveTo(x, 0); context.lineTo(x, height); context.stroke();
  }
  for (let y = 0; y <= height; y += 32) {
    context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke();
  }

  context.font = '10px "Share Tech Mono", Consolas, monospace';
  context.textBaseline = 'middle';
  for (const ringCm of [150, 300, 450, MAP_MAX_RANGE_CM]) {
    const ringRadius = ringCm * scale;
    context.beginPath();
    context.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
    context.strokeStyle = 'rgba(124, 184, 138, 0.48)';
    context.setLineDash([4, 5]);
    context.stroke();
    context.setLineDash([]);
    context.fillStyle = '#75957c';
    context.textAlign = 'left';
    context.fillText(`${ringCm} cm`, centerX + 7, centerY - ringRadius + 11);
  }

  if (hasDistance) {
    const measuredRadius = clamp(distance, 0, MAP_MAX_RANGE_CM) * scale;
    context.beginPath();
    context.arc(centerX, centerY, measuredRadius, 0, Math.PI * 2);
    context.strokeStyle = ringColor;
    context.lineWidth = 2;
    context.setLineDash([]);
    context.stroke();
    context.fillStyle = ringColor;
    context.textAlign = 'center';
    context.fillText(`MEASURED RANGE ${Math.round(distance)} CM${distance > MAP_MAX_RANGE_CM ? ' (RING CLAMPED)' : ''}`, centerX, Math.max(16, centerY - measuredRadius - 13));
  } else if (presence) {
    context.fillStyle = '#ffad42';
    context.textAlign = 'center';
    context.fillText('TARGET DETECTED · DISTANCE UNAVAILABLE', centerX, 25);
  } else {
    context.fillStyle = '#75957c';
    context.textAlign = 'center';
    context.fillText(radarConnected === false ? 'RADAR DISCONNECTED' : 'NO TARGET DETECTED', centerX, 25);
  }

  context.beginPath();
  context.arc(centerX, centerY, 9, 0, Math.PI * 2);
  context.fillStyle = '#20c94d';
  context.fill();
  context.strokeStyle = '#b8ffd0';
  context.lineWidth = 2;
  context.stroke();
  context.fillStyle = '#d8eadb';
  context.textAlign = 'center';
  context.fillText('RADAR', centerX, centerY + 20);
  canvas.setAttribute('aria-label', hasDistance
    ? `Radar detected a target at ${Math.round(distance)} centimeters. The range ring has no directional information.`
    : presence ? 'Radar detected a target but has no distance measurement.' : 'No radar target detected.');

  setText('range-val', hasDistance ? `${Math.round(distance)} CM · ${zone} BAND` : presence ? 'RANGE UNAVAILABLE' : 'NO TARGET');
  const measurementLabel = (range, energy) => {
    const measured = finiteNumber(range, NaN);
    if (!Number.isFinite(measured) || measured <= 0) return 'NO TARGET';
    const confidence = finiteNumber(energy, NaN);
    return `${Math.round(measured)} CM · ENERGY ${Number.isFinite(confidence) ? Math.round(confidence) : '--'}`;
  };
  setText('radar-detail', `MOVING: ${measurementLabel(status.moving_distance_cm, status.moving_energy)} · STATIONARY: ${measurementLabel(status.stationary_distance_cm, status.stationary_energy)}`);
  const espStatus = $('esp-status-cell').querySelector('strong');
  espStatus.textContent = espOnline ? 'ONLINE' : 'OFFLINE';
  espStatus.className = espOnline ? 'connected' : 'disconnected';
  const hasPublisher = status.sensor_device && status.sensor_device !== 'UNKNOWN';
  const lastSeen = hasPublisher ? formatTimestamp(status.last_seen, true) : 'WAITING';
  setText('last-seen', hasPublisher && !status.sensor_connected ? `OFFLINE · ${lastSeen}` : lastSeen);
}

function setCameraState(label, state) {
  setText('camera-feed-state', label);
  $('camera-feed-state').className = `camera-state ${state}`;
}

function showCameraPlaceholder(message) {
  $('camera-placeholder').hidden = false;
  setText('camera-placeholder', message);
  $('camera-image').hidden = true;
}

function snapshotUrl() {
  return `${cameraBaseUrl}/capture?t=${Date.now()}`;
}

function refreshCameraImage() {
  if (!cameraBaseUrl || cameraStreamActive) return;
  setCameraState('CAPTURING IMAGE', 'unknown');
  showCameraPlaceholder('Requesting a JPEG image from the ESP32-CAM...');
  $('camera-image').src = snapshotUrl();
}

function configureCamera(status) {
  const nextBaseUrl = String(status.camera_base_url || '').replace(/\/$/, '');
  const changed = nextBaseUrl !== cameraBaseUrl;
  cameraBaseUrl = nextBaseUrl;
  cameraRefreshSeconds = clamp(finiteNumber(status.camera_refresh_seconds, 5), 2, 60);
  const configured = Boolean(cameraBaseUrl);
  $('capture-button').disabled = !configured;
  $('refresh-image-button').disabled = !configured;
  $('stream-toggle-button').disabled = !configured;
  setText('camera-address', configured ? `CAMERA: ${cameraBaseUrl}` : 'CAMERA: NOT CONFIGURED');

  if (!configured) {
    stopCameraStream(false);
    if (cameraRefreshTimer !== null) window.clearInterval(cameraRefreshTimer);
    cameraRefreshTimer = null;
    showCameraPlaceholder('Set CAMERA_BASE_URL in .env to display images from the ESP32-CAM.');
    setCameraState('CAMERA NOT CONFIGURED', 'unknown');
    return;
  }

  if (changed || cameraRefreshTimer === null) {
    stopCameraStream(false);
    showCameraPlaceholder('Waiting for an image from the camera board...');
    setCameraState('WAITING FOR CAMERA', 'unknown');
    if (cameraRefreshTimer !== null) window.clearInterval(cameraRefreshTimer);
    cameraRefreshTimer = window.setInterval(refreshCameraImage, cameraRefreshSeconds * 1000);
    refreshCameraImage();
  }
}

function stopCameraStream(refreshSnapshot = true) {
  cameraStreamActive = false;
  $('capture-button').disabled = !cameraBaseUrl;
  $('refresh-image-button').disabled = !cameraBaseUrl;
  $('stream-toggle-button').disabled = !cameraBaseUrl;
  $('stream-toggle-button').setAttribute('aria-pressed', 'false');
  setText('stream-toggle-button', 'Start Live Stream');
  if (cameraBaseUrl) {
    $('camera-image').src = '';
    if (refreshSnapshot) refreshCameraImage();
  }
}

function toggleCameraStream() {
  if (!cameraBaseUrl) return;
  if (cameraStreamActive) {
    stopCameraStream();
    return;
  }
  cameraStreamActive = true;
  $('capture-button').disabled = true;
  $('refresh-image-button').disabled = true;
  $('camera-image').src = `${cameraBaseUrl}/stream`;
  $('camera-image').hidden = false;
  $('camera-placeholder').hidden = true;
  $('stream-toggle-button').setAttribute('aria-pressed', 'true');
  setText('stream-toggle-button', 'Stop Live Stream');
  setCameraState('CONNECTING TO STREAM', 'unknown');
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
  configureCamera(status);
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

$('camera-image').addEventListener('load', () => {
  $('camera-image').hidden = false;
  $('camera-placeholder').hidden = true;
  setCameraState(cameraStreamActive ? 'LIVE STREAM CONNECTED' : 'IMAGE RECEIVED', 'connected');
});

$('camera-image').addEventListener('error', () => {
  if (!cameraBaseUrl) return;
  cameraStreamActive = false;
  $('capture-button').disabled = false;
  $('refresh-image-button').disabled = false;
  $('stream-toggle-button').disabled = false;
  $('stream-toggle-button').setAttribute('aria-pressed', 'false');
  setText('stream-toggle-button', 'Start Live Stream');
  showCameraPlaceholder('Camera request failed. Check the camera IP, Wi-Fi, and that the camera server is running.');
  setCameraState('CAMERA UNREACHABLE', 'disconnected');
});

$('capture-button').addEventListener('click', refreshCameraImage);
$('refresh-image-button').addEventListener('click', refreshCameraImage);
$('stream-toggle-button').addEventListener('click', toggleCameraStream);

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
window.addEventListener('resize', () => {
  if (window.lastRadarStatus) renderMap(window.lastRadarStatus, window.lastRadarLevel || 'NORMAL');
});

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
