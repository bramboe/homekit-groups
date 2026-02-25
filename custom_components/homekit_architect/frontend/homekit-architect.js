/**
 * HomeKit Accessory Architect - Configuration Panel
 * Endpoint: /config/homekit-architect
 * Uses WebSocket API: homekit_architect/list_bridges, homekit_architect/bridge_entities, homekit_architect/package_accessory
 */
(function () {
  const DOMAIN = "homekit_architect";

  class HomeKitArchitectPanel extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._hass = null;
      this._bridges = [];
      this._selectedBridgeId = null;
      this._entities = [];
      this._loading = false;
      this._error = null;
    }

    set hass(hass) {
      this._hass = hass;
      if (hass && !this._bridges.length) this._fetchBridges();
    }

    connectedCallback() {
      this._render();
    }

    async _wsSend(type, extra = {}) {
      if (!this._hass?.connection) return null;
      return new Promise((resolve, reject) => {
        const id = Math.round(Math.random() * 1e9);
        const handler = (msg) => {
          if (msg.id !== id) return;
          this._hass.connection.removeEventListener("message", handler);
          if (msg.type === "result" && msg.success) resolve(msg.result);
          else reject(msg.error || { message: "Unknown error" });
        };
        this._hass.connection.addEventListener("message", handler);
        this._hass.connection.sendMessagePromise({ type, id, ...extra }).catch(reject);
      });
    }

    async _fetchBridges() {
      this._loading = true;
      this._error = null;
      this._render();
      try {
        const res = await this._wsSend(`${DOMAIN}/list_bridges`);
        this._bridges = res?.bridges || [];
        this._loading = false;
        this._render();
      } catch (e) {
        this._error = e?.message || String(e);
        this._loading = false;
        this._render();
      }
    }

    async _onBridgeChange(e) {
      const id = e.target?.value;
      this._selectedBridgeId = id || null;
      this._entities = [];
      this._render();
      if (!id) return;
      this._loading = true;
      this._render();
      try {
        const res = await this._wsSend(`${DOMAIN}/bridge_entities`, { bridge_entry_id: id });
        this._entities = res?.entities || [];
      } catch (err) {
        this._error = err?.message || String(err);
      }
      this._loading = false;
      this._render();
    }

    _render() {
      const root = this.shadowRoot;
      if (!root) return;

      const bridge = this._bridges.find((b) => b.entry_id === this._selectedBridgeId);
      const filterInfo = bridge?.filter
        ? `Include: ${(bridge.filter.include_entities?.length || 0)} entities, ${(bridge.filter.include_domains?.length || 0)} domains · Exclude: ${(bridge.filter.exclude_entities?.length || 0)} entities, ${(bridge.filter.exclude_domains?.length || 0)} domains`
        : "";

      root.innerHTML = `
        <style>
          :host { display: block; padding: 16px; font-family: var(--mdc-typography-font-family, Roboto, sans-serif); }
          h1 { font-size: 24px; margin: 0 0 16px 0; }
          .card { background: var(--ha-card-background, var(--card-background-color, #1c1c1c)); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
          select { width: 100%; max-width: 400px; padding: 8px 12px; font-size: 14px; border-radius: 4px; margin-bottom: 12px; }
          .loading, .error { padding: 12px; margin: 8px 0; border-radius: 4px; }
          .loading { background: rgba(255,152,0,0.1); color: var(--primary-color, #ff9800); }
          .error { background: rgba(244,67,54,0.1); color: var(--error-color, #f44336); }
          .filter-info { font-size: 12px; color: var(--secondary-text-color); margin-top: 4px; }
          ul { list-style: none; padding: 0; margin: 8px 0 0 0; max-height: 400px; overflow-y: auto; }
          li { padding: 8px 12px; border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.12)); display: flex; justify-content: space-between; align-items: center; }
          li .domain { font-size: 11px; opacity: 0.8; margin-right: 8px; }
          li .state { font-size: 12px; opacity: 0.9; }
        </style>
        <h1>HomeKit Accessory Architect</h1>
        <p style="margin: 0 0 16px 0; color: var(--secondary-text-color);">
          Select a HomeKit Bridge to inspect its entities and package them into single accessories. Use "Add integration" to create your first accessory, then return here to manage more.
        </p>

        <div class="card">
          <label for="bridge-select"><strong>HomeKit Bridge</strong></label>
          <select id="bridge-select">
            <option value="">-- Select a bridge --</option>
            ${(this._bridges || []).map((b) => `<option value="${b.entry_id}" ${b.entry_id === this._selectedBridgeId ? "selected" : ""}>${this._escape(b.title)}</option>`).join("")}
          </select>
          ${bridge ? `<div class="filter-info">${this._escape(filterInfo)}</div>` : ""}
        </div>

        ${this._loading ? '<div class="loading">Loading…</div>' : ""}
        ${this._error ? `<div class="error">${this._escape(this._error)}</div>` : ""}

        ${this._selectedBridgeId && this._entities.length > 0 ? `
          <div class="card">
            <strong>Entities exposed by this bridge (${this._entities.length})</strong>
            <ul>
              ${this._entities.map((e) => `
                <li>
                  <span><span class="domain">${this._escape(e.domain)}</span> ${this._escape(e.friendly_name || e.entity_id)}</span>
                  <span class="state">${this._escape(e.state ?? "")}</span>
                </li>
              `).join("")}
            </ul>
            <p style="margin-top: 12px; font-size: 13px; color: var(--secondary-text-color);">
              Multi-select and "Package as Accessory" coming in the next update. For now, add accessories via <strong>Settings → Devices & services → Add integration → HomeKit Entity Architect</strong>.
            </p>
          </div>
        ` : this._selectedBridgeId && !this._loading && this._entities.length === 0 ? `
          <div class="card">
            <p>No entities are currently exposed by this bridge, or the filter is restrictive. Adjust the bridge's entity filter in its options, or add entities to its include list.
          </p>
          </div>
        ` : ""}
      `;

      const sel = root.getElementById("bridge-select");
      if (sel) sel.addEventListener("change", (e) => this._onBridgeChange(e));
    }

    _escape(s) {
      if (s == null) return "";
      const div = document.createElement("div");
      div.textContent = s;
      return div.innerHTML;
    }
  }

  customElements.define("homekit-architect-panel", HomeKitArchitectPanel);
})();
