/* BUSY Bar Lovelace card: live display mirror + full device controls.
 * Served by the busybar integration; no manual resource setup needed.
 *
 * Minimal config:  type: custom:busybar-card
 * Options:
 *   prefix: busy_bar          # entity id prefix (from the device name)
 *   entry_id: <config entry>  # only needed with multiple Bars
 *   display: front            # front or back mirror at the top
 *   entities: {}              # per-role entity_id overrides, see README
 */

/* translation_key per role, as registered by this integration */
const ROLE_KEYS = {
  busy: ["switch", "busy"],
  custom: ["switch", "custom_screen"],
  screen: ["select", "busy_screen"],
  mode: ["select", "mode"],
  timer: ["number", "busy_timer"],
  brightness: ["number", "brightness"],
  volume: ["number", "volume"],
  status: ["sensor", "busy_status"],
  top: ["button", "press_top_button"],
  ok: ["button", "press_ok"],
  back: ["button", "press_back"],
  up: ["button", "scroll_up"],
  down: ["button", "scroll_down"],
};

const ROLE_CANDIDATES = {
  busy: ["switch.{p}_busy"],
  custom: ["switch.{p}_custom_screen"],
  screen: ["select.{p}_screen", "select.{p}_busy_screen"],
  mode: ["select.{p}_mode"],
  timer: ["number.{p}_screen_timer", "number.{p}_busy_timer"],
  brightness: ["number.{p}_brightness"],
  volume: ["number.{p}_volume"],
  status: ["sensor.{p}_busy_status"],
  top: ["button.{p}_press_top_button"],
  ok: ["button.{p}_press_ok"],
  back: ["button.{p}_press_back"],
  up: ["button.{p}_scroll_up"],
  down: ["button.{p}_scroll_down"],
};

const MODES = ["busy", "custom", "off", "apps", "settings"];

class BusyBarCard extends HTMLElement {
  static getStubConfig() {
    return { prefix: "busy_bar" };
  }

  setConfig(config) {
    this._config = { prefix: "busy_bar", display: "front", ...config };
    this._entities = null;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._entities) this._resolveEntities();
    this._update();
  }

  connectedCallback() {
    this._startPolling();
  }

  disconnectedCallback() {
    this._stopPolling();
  }

  getCardSize() {
    return 5;
  }

  _resolveEntities() {
    if (!this._hass) return;
    const overrides = this._config.entities || {};
    this._entities = {};

    // Primary: entity registry lookup by integration + translation_key.
    // Survives device renames, which change entity_id prefixes over time.
    const registry = this._hass.entities || {};
    const byDevice = {};
    for (const [id, ent] of Object.entries(registry)) {
      if (ent.platform !== "busybar") continue;
      const dev = ent.device_id || "?";
      (byDevice[dev] = byDevice[dev] || []).push({ id, ent });
    }
    let pool = [];
    if (this._config.device_id && byDevice[this._config.device_id]) {
      pool = byDevice[this._config.device_id];
    } else {
      // Single Bar: flatten; multiple: pick the largest group.
      const groups = Object.values(byDevice);
      pool = groups.sort((a, b) => b.length - a.length)[0] || [];
    }
    for (const [role, [domain, key]] of Object.entries(ROLE_KEYS)) {
      if (overrides[role]) {
        this._entities[role] = overrides[role];
        continue;
      }
      const hit = pool.find(
        ({ id, ent }) => id.startsWith(domain + ".") && ent.translation_key === key
      );
      if (hit) this._entities[role] = hit.id;
    }

    // Fallback: legacy prefix guessing for very old installs.
    const p = this._config.prefix;
    for (const [role, candidates] of Object.entries(ROLE_CANDIDATES)) {
      if (this._entities[role]) continue;
      for (const tpl of candidates) {
        const id = tpl.replace("{p}", p);
        if (this._hass.states[id]) {
          this._entities[role] = id;
          break;
        }
      }
    }
  }

  _state(role) {
    const id = this._entities && this._entities[role];
    return id ? this._hass.states[id] : undefined;
  }

  _call(domain, service, data) {
    this._hass.callService(domain, service, data);
  }

  _press(role) {
    const id = this._entities[role];
    if (id) this._call("button", "press", { entity_id: id });
  }

  /* ---------- screen mirror ---------- */

  _startPolling() {
    if (this._timer) return;
    this._timer = setInterval(() => this._fetchFrame(), 1000);
    this._fetchFrame();
  }

  _stopPolling() {
    clearInterval(this._timer);
    this._timer = null;
  }

  async _fetchFrame() {
    if (!this._hass || document.hidden) return;
    const display = this._config.display;
    let path = `busybar/screen/${display}`;
    if (this._config.entry_id) path += `?entry_id=${this._config.entry_id}`;
    try {
      const frame = await this._hass.callApi("GET", path);
      this._drawFrame(frame);
      this._setOffline(false);
    } catch (e) {
      const detail =
        (e && (e.body?.message || e.body || e.message)) || String(e);
      this._setOffline(true, typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  }

  _setOffline(offline, detail) {
    const el = this.shadowRoot.querySelector(".offline");
    if (!el) return;
    el.style.display = offline ? "block" : "none";
    if (offline) el.textContent = `Screen mirror error: ${detail || "unreachable"}`;
  }

  _drawFrame(frame) {
    const canvas = this.shadowRoot.querySelector("canvas");
    if (!canvas) return;
    const { width, height } = frame;
    const bytes = atob(frame.pixels);
    // Render as round LEDs on black, like the physical matrix.
    const S = 10; // canvas px per LED; CSS scales the canvas down
    if (canvas.width !== width * S) canvas.width = width * S;
    if (canvas.height !== height * S) canvas.height = height * S;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const r = S * 0.42;
    const TAU = 2 * Math.PI;
    for (let i = 0, j = 0; i < width * height; i++) {
      const red = bytes.charCodeAt(j++);
      const grn = bytes.charCodeAt(j++);
      const blu = bytes.charCodeAt(j++);
      if (red + grn + blu < 12) continue; // unlit LED stays black
      const x = (i % width) * S + S / 2;
      const y = ((i / width) | 0) * S + S / 2;
      ctx.fillStyle = `rgb(${red},${grn},${blu})`;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, TAU);
      ctx.fill();
    }
  }

  /* ---------- rendering ---------- */

  _render() {
    const front = this._config.display === "front";
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 12px; }
        .chassis {
          background: #111;
          border-radius: 14px;
          padding: 14px 16px 10px;
          position: relative;
        }
        .topbtn {
          position: absolute;
          top: -7px;
          left: 50%;
          transform: translateX(-50%);
          width: 40%;
          height: 12px;
          background: #2a2a2a;
          border: 1px solid #3a3a3a;
          border-radius: 6px;
          cursor: pointer;
        }
        .topbtn:active { background: #444; }
        .screenwrap { text-align: center; }
        canvas {
          width: 100%;
          max-width: ${front ? "540px" : "480px"};
          ${front ? "" : "image-rendering: pixelated;"}
          background: #000;
          border-radius: 4px;
          aspect-ratio: ${front ? "72 / 16" : "2 / 1"};
        }
        .offline {
          display: none;
          color: #f66;
          font-size: 12px;
          text-align: center;
        }
        .row {
          display: flex;
          gap: 8px;
          align-items: center;
          margin-top: 10px;
          flex-wrap: wrap;
        }
        .modes { display: flex; gap: 4px; flex: 1; }
        .modes button, .keys button {
          flex: 1;
          padding: 6px 8px;
          background: #222;
          color: #ccc;
          border: 1px solid #333;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
          text-transform: capitalize;
        }
        .modes button.active { background: #c62828; color: #fff; border-color: #c62828; }
        .keys { display: flex; gap: 4px; }
        .toggles { display: flex; gap: 8px; flex: 1; }
        .toggles button {
          flex: 1;
          padding: 8px;
          border-radius: 8px;
          border: 1px solid #333;
          background: #222;
          color: #ccc;
          cursor: pointer;
          font-weight: 600;
        }
        .toggles button.on { background: #c62828; border-color: #e53935; color: #fff; }
        select, input[type=number] {
          background: #222;
          color: #eee;
          border: 1px solid #333;
          border-radius: 6px;
          padding: 6px;
        }
        label { color: #999; font-size: 12px; }
        input[type=range] { flex: 1; }
        .status { color: #888; font-size: 12px; margin-top: 8px; text-align: center; }
        .missing { color: #f88; font-size: 12px; }
      </style>
      <ha-card>
        <div class="chassis">
          <div class="topbtn" id="top" title="Top button"></div>
          <div class="screenwrap"><canvas></canvas></div>
          <div class="offline">Bar unreachable</div>
          <div class="row"><div class="modes" id="modes"></div></div>
          <div class="row">
            <div class="toggles">
              <button id="busy">BUSY</button>
              <button id="custom">CUSTOM</button>
            </div>
            <div class="keys">
              <button id="up" title="Scroll up">▲</button>
              <button id="down" title="Scroll down">▼</button>
              <button id="ok" title="OK">OK</button>
              <button id="backb" title="Back">←</button>
            </div>
          </div>
          <div class="row">
            <label>Screen</label><select id="screen"></select>
            <label>Timer</label><input id="timerv" type="number" min="0" max="480" style="width:60px"><label>min</label>
          </div>
          <div class="row">
            <label>💡</label><input id="bright" type="range" min="0" max="100">
            <label>🔊</label><input id="vol" type="range" min="0" max="100">
          </div>
          <div class="status" id="status"></div>
        </div>
      </ha-card>`;

    const q = (sel) => this.shadowRoot.querySelector(sel);
    q("#top").onclick = () => this._press("top");
    q("#ok").onclick = () => this._press("ok");
    q("#backb").onclick = () => this._press("back");
    q("#up").onclick = () => this._press("up");
    q("#down").onclick = () => this._press("down");
    q("#busy").onclick = () => this._toggle("busy");
    q("#custom").onclick = () => this._toggle("custom");
    q("#screen").onchange = (e) =>
      this._call("select", "select_option", {
        entity_id: this._entities.screen,
        option: e.target.value,
      });
    q("#timerv").onchange = (e) =>
      this._call("number", "set_value", {
        entity_id: this._entities.timer,
        value: Number(e.target.value),
      });
    q("#bright").onchange = (e) =>
      this._call("number", "set_value", {
        entity_id: this._entities.brightness,
        value: Number(e.target.value),
      });
    q("#vol").onchange = (e) =>
      this._call("number", "set_value", {
        entity_id: this._entities.volume,
        value: Number(e.target.value),
      });

    const modes = q("#modes");
    for (const mode of MODES) {
      const b = document.createElement("button");
      b.textContent = mode;
      b.onclick = () =>
        this._call("select", "select_option", {
          entity_id: this._entities.mode,
          option: mode,
        });
      b.dataset.mode = mode;
      modes.appendChild(b);
    }
  }

  _toggle(role) {
    const st = this._state(role);
    if (!st) return;
    this._call(
      "switch",
      st.state === "on" ? "turn_off" : "turn_on",
      { entity_id: this._entities[role] }
    );
  }

  _update() {
    if (!this.shadowRoot || !this._entities) return;
    const q = (sel) => this.shadowRoot.querySelector(sel);

    const busy = this._state("busy");
    const custom = this._state("custom");
    q("#busy").classList.toggle("on", busy && busy.state === "on");
    q("#custom").classList.toggle("on", custom && custom.state === "on");

    const mode = this._state("mode");
    for (const b of this.shadowRoot.querySelectorAll("#modes button")) {
      b.classList.toggle("active", mode && mode.state === b.dataset.mode);
    }

    const screen = this._state("screen");
    const sel = q("#screen");
    if (screen && sel && document.activeElement !== sel) {
      const options = screen.attributes.options || [];
      if (sel.options.length !== options.length) {
        sel.innerHTML = options
          .map((o) => `<option value="${o}">${o.replace(/_/g, " ")}</option>`)
          .join("");
      }
      sel.value = screen.state;
    }

    for (const [role, id] of [
      ["timer", "#timerv"],
      ["brightness", "#bright"],
      ["volume", "#vol"],
    ]) {
      const st = this._state(role);
      const el = q(id);
      if (st && el && document.activeElement !== el && st.state !== "unknown") {
        el.value = st.state;
      }
    }

    const status = this._state("status");
    const missing = Object.keys(ROLE_CANDIDATES).filter(
      (r) => !this._entities[r]
    );
    q("#status").innerHTML =
      (status ? `Status: ${status.state}` : "") +
      (missing.length
        ? ` <span class="missing">missing: ${missing.join(", ")} — set prefix or entities in card config</span>`
        : "");
  }
}

/* Define now, and re-assert later: the scoped-custom-element-registry
 * polyfill (shipped by some cards) replaces window.customElements after
 * load, dropping definitions made before it initialized. Re-defining on
 * the final registry resolves Lovelace's whenDefined and rebuilds any
 * "doesn't exist" error cards. */
const ensureDefined = () => {
  try {
    if (!customElements.get("busybar-card")) {
      customElements.define("busybar-card", BusyBarCard);
    }
  } catch (e) {
    /* another copy won the race; fine */
  }
};
ensureDefined();
window.addEventListener("load", ensureDefined);
for (const ms of [1000, 3000, 8000]) setTimeout(ensureDefined, ms);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "busybar-card")) {
  window.customCards.push({
    type: "busybar-card",
    name: "BUSY Bar Card",
    description: "Live display mirror and full controls for the BUSY Bar",
  });
}
console.info(
  "%c BUSYBAR-CARD %c 0.6.7 loaded, element defined ",
  "background:#c62828;color:#fff;font-weight:700",
  "background:#222;color:#fff"
);
