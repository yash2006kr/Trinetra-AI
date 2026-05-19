import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Bell,
  Camera,
  CheckCircle2,
  Database,
  Gauge,
  Layers,
  Maximize2,
  Pause,
  Play,
  Radio,
  RefreshCw,
  Save,
  Scan,
  Search,
  Settings,
  Shield,
  SlidersHorizontal,
  Video,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY || "dev-token";

const modules = [
  "highway_surveillance",
  "traffic_management",
  "smart_city_security",
  "retail_analytics",
  "industrial_safety",
  "smart_parking",
  "railway_surveillance",
  "campus_security",
  "home_security",
  "wildlife_monitoring",
];

function titleize(value) {
  return value.replaceAll("_", " ");
}

async function apiPost(path) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "x-api-key": API_KEY },
  });
  if (!response.ok) throw new Error(`${response.status}`);
  return response.json();
}

async function setCameraPaused(cameraId, paused, moduleName) {
  const action = paused ? "pause" : "resume";
  const query = paused ? "" : `?module=${encodeURIComponent(moduleName)}`;
  return apiPost(`/api/cameras/${cameraId}/${action}${query}`);
}

async function activateCamera(cameraId, moduleName) {
  return apiPost(`/api/cameras/${cameraId}/activate?module=${encodeURIComponent(moduleName)}`);
}

function useApi(path, fallback, interval = 5000) {
  const [data, setData] = useState(fallback);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const response = await fetch(`${API_BASE}${path}`, {
          headers: { "x-api-key": API_KEY },
        });
        if (!response.ok) throw new Error(`${response.status}`);
        const payload = await response.json();
        if (active) {
          setData(payload);
          setError(null);
        }
      } catch (err) {
        if (active) setError(err.message);
      }
    }
    load();
    const timer = setInterval(load, interval);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [path, interval]);

  return { data, error };
}

function formatBytes(value) {
  if (!value) return "0 MB";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let idx = 0;
  while (size > 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(idx < 2 ? 0 : 1)} ${units[idx]}`;
}

function LiveTile({ camera, moduleName, useTracking = false, onOpen }) {
  const cameraId = camera.camera_id;
  const [image, setImage] = useState(null);
  const [connected, setConnected] = useState(false);
  const [streaming, setStreaming] = useState(true);
  const [paused, setPaused] = useState(false);
  const [detections, setDetections] = useState(null);
  const [toggleBusy, setToggleBusy] = useState(false);

  useEffect(() => {
    if (!cameraId || !streaming) return undefined;
    const wsBase = API_BASE.replace(/^http/, "ws");
    const wsUrl = useTracking
      ? `${wsBase}/api/ws/tracking/${cameraId}?module=${encodeURIComponent(moduleName)}`
      : `${wsBase}/api/ws/live/${cameraId}`;
    const socket = new WebSocket(wsUrl);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.paused) {
        setPaused(true);
        setImage(null);
        setDetections(null);
        setConnected(false);
        return;
      }
      setPaused(false);
      setImage(`data:image/jpeg;base64,${payload.jpeg_base64}`);
      setDetections(useTracking ? payload.detections || null : null);
      setConnected(true);
    };
    socket.onerror = () => setConnected(false);
    socket.onclose = () => setConnected(false);
    return () => socket.close();
  }, [cameraId, streaming, moduleName, useTracking]);

  async function toggleStream() {
    if (!cameraId || toggleBusy) return;
    setToggleBusy(true);
    try {
      if (streaming) {
        await setCameraPaused(cameraId, true, moduleName);
        setStreaming(false);
        setPaused(true);
        setImage(null);
        setDetections(null);
        setConnected(false);
      } else {
        await setCameraPaused(cameraId, false, moduleName);
        setPaused(false);
        setStreaming(true);
      }
    } catch {
      setConnected(false);
    } finally {
      setToggleBusy(false);
    }
  }

  const speedHud = useTracking && moduleName === "highway_surveillance" && detections?.speed_limit_kmph != null;

  return (
    <div className={`live-tile ${useTracking ? "tracking-mode" : ""}`}>
      <div className="tile-toolbar">
        <span className={connected && !paused ? "status online" : "status"}>
          <Radio size={14} /> {paused ? `${cameraId} (paused)` : cameraId}
          {useTracking && !paused && <small className="tracking-badge">YOLO</small>}
        </span>
        <div className="tile-actions">
          <button
            aria-label={streaming ? "pause camera" : "start camera"}
            title={streaming ? "Pause camera" : "Start camera"}
            disabled={toggleBusy}
            onClick={toggleStream}
          >
            {streaming ? <Pause size={15} /> : <Play size={15} />}
          </button>
          <button aria-label="open live viewer" title="Open live viewer" onClick={() => onOpen(camera)}>
            <Maximize2 size={15} />
          </button>
        </div>
      </div>
      {image ? (
        <img src={image} alt={useTracking ? `${cameraId} YOLO tracking` : `${cameraId} live webcam`} />
      ) : (
        <div className={`video-placeholder ${paused ? "paused" : ""}`}>
          <Video size={36} />
          <span>
            {paused
              ? "Camera paused - press Play to turn on"
              : useTracking
                ? "Loading webcam and YOLO model..."
                : "Waiting for webcam"}
          </span>
        </div>
      )}
      {detections && !paused && (
        <div className={`detection-hud ${detections.violations ? "has-violations" : ""}`}>
          {speedHud ? (
            <>
              <span>Limit {detections.speed_limit_kmph} km/h</span>
              <span>Max {detections.max_speed_kmph ?? 0} km/h</span>
            </>
          ) : (
            <span>{detections.detection_count} detected</span>
          )}
          {detections.violations > 0 && <span className="violation-pill">{detections.violations} alert</span>}
        </div>
      )}
    </div>
  );
}

function EventTable({ events, onSelect }) {
  return (
    <div className="event-table">
      <div className="table-row table-head">
        <span>Event</span>
        <span>Module</span>
        <span>Camera</span>
        <span>Score</span>
        <span>Tags</span>
      </div>
      {events.slice(0, 8).map((event) => (
        <button className="table-row row-button" key={event.event_id} onClick={() => onSelect(event)}>
          <span>{event.event_id.slice(0, 8)}</span>
          <span>{titleize(event.module)}</span>
          <span>{event.camera_id}</span>
          <span>{Math.round(event.score * 100)}%</span>
          <span>{event.tags.slice(0, 3).join(", ") || "motion"}</span>
        </button>
      ))}
      {!events.length && <div className="empty">No events yet</div>}
    </div>
  );
}

function Heatmap() {
  const cells = Array.from({ length: 48 }, (_, idx) => {
    const intensity = Math.abs(Math.sin(idx * 0.58)) * 0.9 + 0.1;
    return <span key={idx} style={{ opacity: intensity }} />;
  });
  return <div className="heatmap">{cells}</div>;
}

function Timeline({ events }) {
  const cells = events.length ? events.slice(0, 28) : Array.from({ length: 28 }, (_, idx) => ({ event_id: `empty-${idx}`, score: 0 }));
  return (
    <div className="timeline">
      {cells.map((event) => (
        <span
          key={event.event_id}
          className={event.score >= 0.65 ? "hot" : event.score >= 0.3 ? "warm" : ""}
          title={event.tags ? `${event.module} ${event.tags.join(", ")}` : "No event"}
        />
      ))}
    </div>
  );
}

function Modal({ title, children, onClose }) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <div className="modal-head">
          <strong>{title}</strong>
          <button aria-label="close" title="Close" onClick={onClose}><X size={18} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function SettingsPanel({ cameras, storage, selectedModule, onClose }) {
  return (
    <Modal title="Settings" onClose={onClose}>
      <div className="settings-grid">
        <label>API Base<input readOnly value={API_BASE} /></label>
        <label>Active Module<input readOnly value={selectedModule} /></label>
        <label>Database<input readOnly value="SQLite / MongoDB via backend config" /></label>
        <label>Recording Root<input readOnly value={storage.recording_root || "data/recordings"} /></label>
      </div>
      <div className="modal-section">
        <strong>Camera Health</strong>
        {cameras.map((camera) => (
          <div className="health-row" key={camera.camera_id}>
            {camera.connected ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <span>{camera.camera_id}</span>
            <small>{camera.connected ? "Connected" : "Starting / unavailable"}</small>
          </div>
        ))}
      </div>
    </Modal>
  );
}

function ModelControls({ selectedModule, onClose }) {
  const [confidence, setConfidence] = useState(35);
  const [recording, setRecording] = useState(true);
  const [edgeMode, setEdgeMode] = useState(true);
  const [saved, setSaved] = useState(false);

  return (
    <Modal title="AI Model Controls" onClose={onClose}>
      <div className="control-stack">
        <label>
          Confidence Threshold
          <input type="range" min="10" max="90" value={confidence} onChange={(event) => setConfidence(event.target.value)} />
          <span>{confidence}%</span>
        </label>
        <label className="switch"><input type="checkbox" checked={recording} onChange={() => setRecording(!recording)} /> Motion recording</label>
        <label className="switch"><input type="checkbox" checked={edgeMode} onChange={() => setEdgeMode(!edgeMode)} /> Edge AI mode</label>
        <div className="model-summary">
          <span>{titleize(selectedModule)}</span>
          <span>YOLOv8 / YOLOv11 ready</span>
          <span>CUDA auto-detect</span>
        </div>
        <button className="primary-action" onClick={() => setSaved(true)}><Save size={16} /> Apply Controls</button>
        {saved && <p className="success-text">Demo controls applied locally. Backend config stays safe until you persist it.</p>}
      </div>
    </Modal>
  );
}

function LiveViewer({ camera, moduleName, useTracking, onClose }) {
  return (
    <Modal title={`${useTracking ? "YOLO tracking" : "Webcam"} — ${camera.name || camera.camera_id}`} onClose={onClose}>
      <div className="viewer-frame viewer-frame-large">
        <LiveTile camera={camera} moduleName={moduleName} useTracking={useTracking} onOpen={() => {}} />
      </div>
    </Modal>
  );
}

function EventDetails({ event, onClose }) {
  const [clipSrc, setClipSrc] = useState(null);

  useEffect(() => {
    let objectUrl;
    if (!event.clip_exists) {
      setClipSrc(null);
      return undefined;
    }
    async function loadClip() {
      const response = await fetch(`${API_BASE}/api/events/${event.event_id}/clip`, {
        headers: { "x-api-key": API_KEY },
      });
      if (!response.ok) return;
      const blob = await response.blob();
      objectUrl = URL.createObjectURL(blob);
      setClipSrc(objectUrl);
    }
    loadClip();
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [event.event_id, event.clip_exists]);

  return (
    <Modal title={`Event ${event.event_id.slice(0, 8)}`} onClose={onClose}>
      <div className="event-detail">
        <p><strong>Module:</strong> {titleize(event.module)}</p>
        <p><strong>Camera:</strong> {event.camera_id}</p>
        <p><strong>Score:</strong> {Math.round(event.score * 100)}%</p>
        <p><strong>Tags:</strong> {event.tags.join(", ") || "motion"}</p>
        {clipSrc ? (
          <video className="event-clip" controls src={clipSrc} />
        ) : (
          <p className="panel-help">No video file for this row. Test Event rows are database-only. Real clips need the Python pipeline.</p>
        )}
      </div>
    </Modal>
  );
}

function App() {
  const [selectedModule, setSelectedModule] = useState("highway_surveillance");
  const [filterText, setFilterText] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeModal, setActiveModal] = useState(null);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [toast, setToast] = useState("");
  const [detectionOn, setDetectionOn] = useState(true);
  const [viewerTracking, setViewerTracking] = useState(true);

  const { data: events } = useApi(`/api/events?module=${selectedModule}&limit=80&refresh=${refreshKey}`, []);
  const { data: alerts } = useApi(`/api/alerts?limit=40&refresh=${refreshKey}`, []);
  const { data: summary } = useApi(`/api/analytics/summary?refresh=${refreshKey}`, { total_events: 0, events_by_module: {} });
  const { data: storage } = useApi(`/api/storage?refresh=${refreshKey}`, {});
  const { data: cameras } = useApi(`/api/cameras?refresh=${refreshKey}`, []);

  const chartData = useMemo(
    () => Object.entries(summary.events_by_module || {}).map(([name, count]) => ({ name: titleize(name), count })),
    [summary]
  );

  const cameraList = cameras.length ? cameras : [{ camera_id: "webcam_0", name: "Webcam 1", connected: false, running: true, active: true }];
  const activeCamera = cameraList.find((camera) => camera.active) || cameraList[0];
  const [selectedCameraId, setSelectedCameraId] = useState(activeCamera?.camera_id || "webcam_0");

  useEffect(() => {
    if (activeCamera?.camera_id && activeCamera.camera_id !== selectedCameraId) {
      setSelectedCameraId(activeCamera.camera_id);
    }
  }, [activeCamera?.camera_id]);

  const displayCamera = cameraList.find((camera) => camera.camera_id === selectedCameraId) || activeCamera;

  async function switchWebcam(cameraId) {
    if (!cameraId || cameraId === selectedCameraId) return;
    try {
      await activateCamera(cameraId, selectedModule);
      setSelectedCameraId(cameraId);
      setToast(`Switched to ${cameraList.find((c) => c.camera_id === cameraId)?.name || cameraId}`);
      setRefreshKey((value) => value + 1);
      setTimeout(() => setToast(""), 2000);
    } catch {
      setToast("Could not switch webcam");
      setTimeout(() => setToast(""), 2500);
    }
  }
  const filteredEvents = events.filter((event) => {
    const haystack = `${event.event_id} ${event.module} ${event.camera_id} ${(event.tags || []).join(" ")}`.toLowerCase();
    return haystack.includes(filterText.toLowerCase());
  });
  const usedPct = storage.disk_total_bytes ? Math.round((storage.disk_used_bytes / storage.disk_total_bytes) * 100) : 0;

  async function runDemoAction(kind) {
    const cameraId = selectedCameraId || cameraList[0]?.camera_id || "webcam_0";
    const path = kind === "alert"
      ? `/api/demo/alert?module=${selectedModule}&camera_id=${cameraId}`
      : `/api/demo/event?module=${selectedModule}&camera_id=${cameraId}`;
    await apiPost(path);
    setToast(kind === "alert" ? "Test alert added to the list" : "Test event added to the table");
    setRefreshKey((value) => value + 1);
    setTimeout(() => setToast(""), 2500);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><Shield size={24} /> <span>SmartVision</span></div>
        <nav>
          {modules.map((name) => (
            <button
              key={name}
              className={selectedModule === name ? "active" : ""}
              onClick={() => setSelectedModule(name)}
              title={titleize(name)}
            >
              <Layers size={16} />
              <span>{titleize(name)}</span>
            </button>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Monitoring Console</p>
            <h1>{titleize(selectedModule)}</h1>
          </div>
          <div className="actions">
            <div className="search"><Search size={16} /><input value={filterText} onChange={(event) => setFilterText(event.target.value)} placeholder="Filter events" /></div>
            <button type="button" title="Model controls" onClick={() => setActiveModal("models")}><SlidersHorizontal size={18} /></button>
            <button type="button" title="Settings" onClick={() => setActiveModal("settings")}><Settings size={18} /></button>
          </div>
        </header>

        {toast && <div className="toast"><CheckCircle2 size={16} /> {toast}</div>}

        <section className="kpis">
          <article><Activity size={18} /><span>{summary.total_events || 0}</span><label>Events</label></article>
          <article><Bell size={18} /><span>{alerts.length}</span><label>Alerts</label></article>
          <article><Camera size={18} /><span>{cameraList.length}</span><label>Cameras</label></article>
          <article><Database size={18} /><span>{usedPct}%</span><label>Disk used</label></article>
        </section>

        <section className="grid">
          <div className="panel live-panel live-panel-featured">
            <div className="panel-title live-panel-head">
              <span><Camera size={18} /> Live Video {detectionOn ? "+ YOLO Detection" : ""}</span>
              <div className="live-panel-controls">
                <label className="camera-select">
                  <span>Webcam</span>
                  <select value={selectedCameraId} onChange={(event) => switchWebcam(event.target.value)}>
                    {cameraList.map((camera) => (
                      <option key={camera.camera_id} value={camera.camera_id}>
                        {camera.name || camera.camera_id}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="button" className={`toggle-detection ${detectionOn ? "on" : ""}`} onClick={() => setDetectionOn(!detectionOn)}>
                  <Scan size={15} /> {detectionOn ? "Detection ON" : "Detection OFF"}
                </button>
                <button type="button" className="panel-action" onClick={() => setRefreshKey((value) => value + 1)} title="Refresh cameras">
                  <RefreshCw size={15} />
                </button>
              </div>
            </div>
            <p className="panel-help">Green box = OK, red box = alert. First load may take a few seconds while YOLO starts.</p>
            {displayCamera && (
              <LiveTile
                key={`${displayCamera.camera_id}-${detectionOn}`}
                camera={displayCamera}
                moduleName={selectedModule}
                useTracking={detectionOn}
                onOpen={(item) => {
                  setSelectedCamera(item);
                  setViewerTracking(detectionOn);
                  setActiveModal("viewer");
                }}
              />
            )}
          </div>

          <div className="panel alerts-panel">
            <div className="panel-title">
              <span><Bell size={18} /> Real-Time Alerts</span>
              <button
                className="panel-action text"
                title="Inserts a fake alert into the database so you can see how the alerts panel looks"
                onClick={() => runDemoAction("alert")}
              >
                Test Alert
              </button>
            </div>
            <p className="panel-help">Test Alert = sample notification only (not from the camera).</p>
            <div className="alert-list">
              {alerts.slice(0, 7).map((alert) => (
                <div className={`alert priority-${alert.priority}`} key={alert.alert_id}>
                  <strong>{alert.title}</strong>
                  <span>{alert.camera_id}</span>
                </div>
              ))}
              {!alerts.length && <div className="empty">No active alerts</div>}
            </div>
          </div>

          <div className="panel analytics-panel">
            <div className="panel-title"><span><Gauge size={18} /> Analytics</span></div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" hide />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#2f80ed" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="panel heat-panel">
            <div className="panel-title"><span><Activity size={18} /> Congestion Heatmap</span></div>
            <Heatmap />
          </div>

          <div className="panel events-panel">
            <div className="panel-title">
              <span><Video size={18} /> Event Playback</span>
              <button
                className="panel-action text"
                title="Inserts a fake motion event into the database so you can see the events table"
                onClick={() => runDemoAction("event")}
              >
                Test Event
              </button>
            </div>
            <p className="panel-help">Test Event = sample row only (not a real recording). Real clips come from the Python pipeline.</p>
            <EventTable events={filteredEvents} onSelect={(event) => setSelectedEvent(event)} />
          </div>

          <div className="panel system-panel">
            <div className="panel-title"><span><Database size={18} /> Storage and Timeline</span></div>
            <div className="storage-bar"><span style={{ width: `${usedPct}%` }} /></div>
            <div className="storage-meta">
              <span>{formatBytes(storage.recordings_bytes)} recordings</span>
              <span>{formatBytes(storage.disk_free_bytes)} free</span>
            </div>
            <Timeline events={filteredEvents} />
          </div>
        </section>
      </section>

      {activeModal === "settings" && <SettingsPanel cameras={cameraList} storage={storage} selectedModule={selectedModule} onClose={() => setActiveModal(null)} />}
      {activeModal === "models" && <ModelControls selectedModule={selectedModule} onClose={() => setActiveModal(null)} />}
      {activeModal === "viewer" && selectedCamera && (
        <LiveViewer
          camera={selectedCamera}
          moduleName={selectedModule}
          useTracking={viewerTracking}
          onClose={() => setActiveModal(null)}
        />
      )}
      {selectedEvent && <EventDetails event={selectedEvent} onClose={() => setSelectedEvent(null)} />}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
