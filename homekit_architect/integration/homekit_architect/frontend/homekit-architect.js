/**
 * HomeKit Accessory Architect - Configuration Panel
 * Endpoint: /config/homekit-architect
 * WebSocket: homekit_architect/list_bridges, bridge_entities, package_accessory
 */
(function () {
  const DOMAIN = "homekit_architect";

  const ACCESSORY_TYPES = [
    { value: "lock", label: "Smart Lock", template_id: "security_lock" },
    { value: "cover", label: "Garage Door", template_id: "garage_door" },
  ];

  const SLOTS_BY_TEMPLATE = {
    security_lock: {
      action_slot: "Lock actuator (switch/lock)",
      state_slot: "State sensor (e.g. door contact)",
      battery_slot: "Battery (optional)",
      obstruction_slot: "Obstruction/jam (optional)",
    },
    garage_door: {
      actuator_slot: "Open/Close actuator",
      position_sensor_slot: "Position sensor (door contact/cover)",
      battery_slot: "Battery (optional)",
    },
  };

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
      this._success = null;
      this._search = "";
      this._domainFilter = new Set();
      this._selectedIds = new Set();
      this._modalOpen = false;
      this._packageDisplayName = "";
      this._packageType = "lock";
      this._packageHideSources = true;
      this._packageSlotMapping = {};
      this._packageSubmitting = false;
    }

    set hass(hass) {
      this._hass = hass;
      if (hass && !this._bridges.length) {
        this._fetchBridges().catch((e) => {
          this._error = e?.message || String(e);
          this._loading = false;
          this._render();
        });
      }
    }

    connectedCallback() {
      this._render();
    }

    async _wsSend(type, extra = {}) {
      const conn = this._hass?.connection;
      if (!conn) return null;
      return new Promise((resolve, reject) => {
        const id = Math.round(Math.random() * 1e9);
        const payload = { type, id, ...extra };
        const handler = (ev) => {
          const msg = ev.detail !== undefined ? ev.detail : ev;
          if (msg.id !== id) return;
          conn.removeEventListener("message", handler);
          clearTimeout(timer);
          if (msg.type === "result" && msg.success) resolve(msg.result);
          else reject(msg.error || { message: (msg.error && msg.error.message) || "Unknown error" });
        };
        conn.addEventListener("message", handler);
        const timer = setTimeout(() => {
          conn.removeEventListener("message", handler);
          reject(new Error("WebSocket timeout"));
        }, 15000);
        if (typeof conn.sendMessagePromise === "function") {
          conn.sendMessagePromise(payload).catch(reject);
        } else if (typeof conn.sendMessage === "function") {
          conn.sendMessage(payload);
        } else {
          clearTimeout(timer);
          conn.removeEventListener("message", handler);
          reject(new Error("No WebSocket send method"));
        }
      });
    }

    async _fetchBridges() {
      this._loading = true;
      this._error = null;
      this._render();
      try {
        const res = await this._wsSend(`${DOMAIN}/list_bridges`);
        this._bridges = res?.bridges || [];
      } catch (e) {
        this._error = e?.message || String(e);
      }
      this._loading = false;
      this._render();
    }

    async _onBridgeChange(e) {
      const id = e.target?.value || null;
      this._selectedBridgeId = id;
      this._entities = [];
      this._selectedIds.clear();
      this._error = null;
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

    _filteredEntities() {
      let list = this._entities || [];
      const q = (this._search || "").toLowerCase().trim();
      if (q) {
        list = list.filter(
          (e) =>
            (e.entity_id && e.entity_id.toLowerCase().includes(q)) ||
            (e.friendly_name && e.friendly_name.toLowerCase().includes(q))
        );
      }
      if (this._domainFilter.size > 0) {
        list = list.filter((e) => e.domain && this._domainFilter.has(e.domain));
      }
      return list;
    }

    _domains() {
      const set = new Set();
      (this._entities || []).forEach((e) => e.domain && set.add(e.domain));
      return Array.from(set).sort();
    }

    _onSearchInput(e) {
      this._search = e.target?.value || "";
      this._render();
    }

    _onDomainToggle(domain) {
      if (this._domainFilter.has(domain)) this._domainFilter.delete(domain);
      else this._domainFilter.add(domain);
      this._render();
    }

    _onEntityCheck(e, entityId) {
      if (e.target?.checked) this._selectedIds.add(entityId);
      else this._selectedIds.delete(entityId);
      this._render();
    }

    _onSelectAll(checked) {
      const list = this._filteredEntities();
      if (checked) list.forEach((e) => e.entity_id && this._selectedIds.add(e.entity_id));
      else list.forEach((e) => e.entity_id && this._selectedIds.delete(e.entity_id));
      this._render();
    }

    _openPackageModal() {
      this._modalOpen = true;
      this._packageDisplayName = "";
      this._packageType = "lock";
      this._packageHideSources = true;
      this._packageSlotMapping = this._suggestSlotMapping(this._packageType);
      this._packageSubmitting = false;
      this._error = null;
      this._success = null;
      this._render();
    }

    _closeModal() {
      this._modalOpen = false;
      this._render();
    }

    _suggestSlotMapping(accessoryType) {
      const typeInfo = ACCESSORY_TYPES.find((t) => t.value === accessoryType);
      const templateId = typeInfo?.template_id || "security_lock";
      const ids = Array.from(this._selectedIds);
      const byDomain = {};
      ids.forEach((eid) => {
        const d = (eid || "").split(".")[0];
        if (!byDomain[d]) byDomain[d] = [];
        byDomain[d].push(eid);
      });
      const mapping = {};
      if (templateId === "security_lock") {
        mapping.action_slot = (byDomain.lock && byDomain.lock[0]) || (byDomain.switch && byDomain.switch[0]) || ids[0];
        mapping.state_slot = (byDomain.binary_sensor && byDomain.binary_sensor[0]) || ids[1] || ids[0];
        if (byDomain.sensor && byDomain.sensor[0]) mapping.battery_slot = byDomain.sensor[0];
        if (byDomain.binary_sensor && byDomain.binary_sensor[1]) mapping.obstruction_slot = byDomain.binary_sensor[1];
      } else {
        mapping.actuator_slot = (byDomain.cover && byDomain.cover[0]) || (byDomain.switch && byDomain.switch[0]) || ids[0];
        mapping.position_sensor_slot = (byDomain.binary_sensor && byDomain.binary_sensor[0]) || (byDomain.cover && byDomain.cover[0]) || ids[1] || ids[0];
        if (byDomain.sensor && byDomain.sensor[0]) mapping.battery_slot = byDomain.sensor[0];
      }
      return mapping;
    }

    _onPackageTypeChange(e) {
      this._packageType = e.target?.value || "lock";
      this._packageSlotMapping = this._suggestSlotMapping(this._packageType);
      this._render();
    }

    async _submitPackage() {
      const displayName = (this._packageDisplayName || "").trim() || "Accessory";
      const entityIds = Array.from(this._selectedIds);
      if (!entityIds.length || !this._selectedBridgeId) return;
      this._packageSubmitting = true;
      this._error = null;
      this._success = null;
      this._render();
      try {
        const res = await this._wsSend(`${DOMAIN}/package_accessory`, {
          bridge_entry_id: this._selectedBridgeId,
          display_name: displayName,
          accessory_type: this._packageType,
          entity_ids: entityIds,
          slot_mapping: this._packageSlotMapping,
          hide_sources: this._packageHideSources,
        });
        this._success = `Created "${res?.title || displayName}". Restart Home Assistant or wait for the new entity to appear.`;
        this._modalOpen = false;
        this._selectedIds.clear();
      } catch (err) {
        this._error = err?.message || String(err);
      }
      this._packageSubmitting = false;
      this._render();
    }

    _render() {
      const root = this.shadowRoot;
      if (!root) return;

      const bridge = this._bridges.find((b) => b.entry_id === this._selectedBridgeId);
      const filterInfo = bridge?.filter
        ? `Include: ${(bridge.filter.include_entities?.length || 0)} entities, ${(bridge.filter.include_domains?.length || 0)} domains · Exclude: ${(bridge.filter.exclude_entities?.length || 0)} entities, ${(bridge.filter.exclude_domains?.length || 0)} domains`
        : "";
      const filtered = this._filteredEntities();
      const domains = this._domains();
      const selectedCount = this._selectedIds.size;
      const typeInfo = ACCESSORY_TYPES.find((t) => t.value === this._packageType);
      const slotLabels = typeInfo ? (SLOTS_BY_TEMPLATE[typeInfo.template_id] || {}) : {};

      root.innerHTML = `
        <style>
          :host { display: block; padding: 16px; font-family: var(--mdc-typography-font-family, Roboto, sans-serif); }
          h1 { font-size: 24px; margin: 0 0 16px 0; }
          .card { background: var(--ha-card-background, var(--card-background-color, #1c1c1c)); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
          select, input[type="text"] { width: 100%; max-width: 400px; padding: 8px 12px; font-size: 14px; border-radius: 4px; margin-bottom: 8px; box-sizing: border-box; }
          .loading, .error, .success { padding: 12px; margin: 8px 0; border-radius: 4px; }
          .loading { background: rgba(255,152,0,0.1); color: var(--primary-color, #ff9800); }
          .error { background: rgba(244,67,54,0.1); color: var(--error-color, #f44336); }
          .success { background: rgba(76,175,80,0.1); color: var(--success-color, #4caf50); }
          .filter-info { font-size: 12px; color: var(--secondary-text-color); margin-top: 4px; }
          .toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 12px; }
          .toolbar input[type="text"] { max-width: 240px; margin: 0; }
          .domain-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
          .domain-chip { padding: 4px 10px; border-radius: 16px; font-size: 12px; cursor: pointer; background: var(--secondary-background-color, #2c2c2c); }
          .domain-chip.active { background: var(--primary-color, #03a9f4); color: #fff; }
          ul { list-style: none; padding: 0; margin: 0; max-height: 360px; overflow-y: auto; }
          li { padding: 8px 12px; border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.12)); display: flex; align-items: center; gap: 10px; }
          li label { flex: 1; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
          li .domain { font-size: 11px; opacity: 0.8; margin-right: 8px; }
          li .state { font-size: 12px; opacity: 0.9; }
          .btn { padding: 8px 16px; border-radius: 4px; font-size: 14px; cursor: pointer; border: none; background: var(--primary-color, #03a9f4); color: #fff; }
          .btn:disabled { opacity: 0.5; cursor: not-allowed; }
          .btn.secondary { background: var(--secondary-background-color, #2c2c2c); }
          .modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999; }
          .modal { background: var(--ha-card-background, #1c1c1c); border-radius: 12px; padding: 24px; max-width: 480px; width: 90%; max-height: 90vh; overflow-y: auto; }
          .modal h2 { margin: 0 0 16px 0; font-size: 20px; }
          .modal .field { margin-bottom: 14px; }
          .modal .field label { display: block; margin-bottom: 4px; font-size: 12px; color: var(--secondary-text-color); }
          .modal .actions { margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end; }
          .modal select.slot { width: 100%; max-width: none; margin-top: 4px; }
        </style>

        <h1>HomeKit Accessory Architect</h1>
        <p style="margin: 0 0 16px 0; color: var(--secondary-text-color);">
          Select a HomeKit Bridge, then multi-select entities to package into a single accessory. Optionally hide the source entities from HomeKit (ghosting).
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
        ${this._success ? `<div class="success">${this._escape(this._success)}</div>` : ""}

        ${this._selectedBridgeId && this._entities.length > 0 ? `
          <div class="card">
            <strong>Entities exposed by this bridge</strong>
            <div class="toolbar">
              <input type="text" id="search-input" placeholder="Search entities…" value="${this._escape(this._search)}" />
              <label><input type="checkbox" id="select-all" /> Select all (filtered)</label>
              <button class="btn" id="btn-package" ${selectedCount === 0 ? "disabled" : ""}>Package as Accessory (${selectedCount})</button>
            </div>
            <div class="domain-chips">
              ${domains.map((d) => `<span class="domain-chip ${this._domainFilter.has(d) ? "active" : ""}" data-domain="${this._escape(d)}">${this._escape(d)}</span>`).join("")}
            </div>
            <ul id="entity-list">
              ${filtered.map((e) => {
                const safeId = "chk-" + (e.entity_id || "").replace(/[^a-zA-Z0-9_-]/g, "_");
                return `
                <li>
                  <input type="checkbox" id="${safeId}" data-entity-id="${this._escape(e.entity_id)}" ${this._selectedIds.has(e.entity_id) ? "checked" : ""} />
                  <label for="${safeId}">
                    <span><span class="domain">${this._escape(e.domain)}</span> ${this._escape(e.friendly_name || e.entity_id)}</span>
                    <span class="state">${this._escape(e.state ?? "")}</span>
                  </label>
                </li>
              `;
              }).join("")}
            </ul>
            ${filtered.length === 0 ? "<p style='margin-top:8px;color:var(--secondary-text-color);'>No entities match the search or domain filter.</p>" : ""}
          </div>
        ` : this._selectedBridgeId && !this._loading && this._entities.length === 0 ? `
          <div class="card">
            <p>No entities are currently exposed by this bridge. Adjust the bridge's entity filter in its options.</p>
          </div>
        ` : ""}

        ${this._modalOpen ? `
          <div class="modal-backdrop" id="modal-backdrop">
            <div class="modal">
              <h2>Package as Accessory</h2>
              <div class="field">
                <label>Display name</label>
                <input type="text" id="modal-display-name" placeholder="e.g. Ventilation Fan" value="${this._escape(this._packageDisplayName)}" />
              </div>
              <div class="field">
                <label>Accessory type</label>
                <select id="modal-type">
                  ${ACCESSORY_TYPES.map((t) => `<option value="${t.value}" ${t.value === this._packageType ? "selected" : ""}>${this._escape(t.label)}</option>`).join("")}
                </select>
              </div>
              <div class="field">
                <label><input type="checkbox" id="modal-hide-sources" ${this._packageHideSources ? "checked" : ""} /> Hide source entities from HomeKit</label>
              </div>
              <div class="field">
                <label>Slot mapping (assign entities to roles)</label>
                ${Object.entries(slotLabels).map(([slotKey, slotLabel]) => {
                  const current = this._packageSlotMapping[slotKey];
                  const options = ["", ...Array.from(this._selectedIds)].map((eid) => `<option value="${this._escape(eid)}" ${eid === current ? "selected" : ""}>${this._escape(eid || "--")}</option>`).join("");
                  return `<div style="margin-bottom:6px;"><span style="font-size:12px;">${this._escape(slotLabel)}</span><select class="slot" data-slot="${this._escape(slotKey)}">${options}</select></div>`;
                }).join("")}
              </div>
              <div class="actions">
                <button class="btn secondary" id="modal-cancel">Cancel</button>
                <button class="btn" id="modal-submit" ${this._packageSubmitting ? "disabled" : ""}>${this._packageSubmitting ? "Creating…" : "Create"}</button>
              </div>
            </div>
          </div>
        ` : ""}
      `;

      const sel = root.getElementById("bridge-select");
      if (sel) sel.addEventListener("change", (e) => this._onBridgeChange(e));
      const searchInput = root.getElementById("search-input");
      if (searchInput) searchInput.addEventListener("input", (e) => this._onSearchInput(e));
      const selectAll = root.getElementById("select-all");
      if (selectAll) {
        selectAll.checked = filtered.length > 0 && filtered.every((e) => this._selectedIds.has(e.entity_id));
        selectAll.addEventListener("change", (e) => this._onSelectAll(e.target?.checked));
      }
      const btnPackage = root.getElementById("btn-package");
      if (btnPackage) btnPackage.addEventListener("click", () => this._openPackageModal());
      root.querySelectorAll(".domain-chip").forEach((el) => {
        el.addEventListener("click", () => this._onDomainToggle(el.getAttribute("data-domain")));
      });
      root.querySelectorAll("#entity-list input[type=checkbox]").forEach((el) => {
        const entityId = el.getAttribute("data-entity-id");
        if (entityId) el.addEventListener("change", (e) => this._onEntityCheck(e, entityId));
      });

      if (this._modalOpen) {
        const displayNameEl = root.getElementById("modal-display-name");
        if (displayNameEl) {
          displayNameEl.value = this._packageDisplayName;
          displayNameEl.addEventListener("input", (e) => { this._packageDisplayName = e.target?.value || ""; });
        }
        const typeEl = root.getElementById("modal-type");
        if (typeEl) {
          typeEl.value = this._packageType;
          typeEl.addEventListener("change", (e) => this._onPackageTypeChange(e));
        }
        const hideEl = root.getElementById("modal-hide-sources");
        if (hideEl) {
          hideEl.checked = this._packageHideSources;
          hideEl.addEventListener("change", (e) => { this._packageHideSources = e.target?.checked; });
        }
        root.querySelectorAll(".modal select.slot").forEach((sel) => {
          const slotKey = sel.getAttribute("data-slot");
          if (slotKey) {
            sel.value = this._packageSlotMapping[slotKey] || "";
            sel.addEventListener("change", (e) => {
              this._packageSlotMapping = { ...this._packageSlotMapping, [slotKey]: e.target?.value || "" };
            });
          }
        });
        root.getElementById("modal-backdrop")?.addEventListener("click", (e) => { if (e.target.id === "modal-backdrop") this._closeModal(); });
        root.getElementById("modal-cancel")?.addEventListener("click", () => this._closeModal());
        root.getElementById("modal-submit")?.addEventListener("click", () => this._submitPackage());
      }
    }

    _escape(s) {
      if (s == null) return "";
      const div = document.createElement("div");
      div.textContent = String(s);
      return div.innerHTML;
    }
  }

  customElements.define("homekit-architect-panel", HomeKitArchitectPanel);
})();
