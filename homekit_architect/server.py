#!/usr/bin/env python3
"""
HomeKit Entity Architect – App Web UI (ingress).
Full management interface: bridge selection, entity picker, package-as-accessory,
and automated ghosting. Calls the HA REST API via the Supervisor proxy.

Per https://developers.home-assistant.io/docs/apps/tutorial/
and https://developers.home-assistant.io/docs/apps/presentation/#ingress
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

LISTEN_PORT = 8099
SOURCE = "/usr/share/homekit_architect/homekit_architect"
CONFIG_DIRS = ["/config", "/homeassistant"]
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HA_API = "http://supervisor/core/api"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ha_request(method, path, data=None):
    url = f"{HA_API}{path}"
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HA API {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"}
    except Exception as e:
        return {"error": str(e)}


def find_config():
    for d in CONFIG_DIRS:
        if os.path.isdir(d) and os.access(d, os.W_OK):
            return d
    return os.environ.get("CONFIG", "/config")


def run_install():
    config = find_config()
    target = os.path.join(config, "custom_components", "homekit_architect")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if os.path.exists(target):
        shutil.rmtree(target)
    subprocess.run(["cp", "-r", SOURCE, target], check=True, capture_output=True, text=True)
    return target


def get_status():
    config = find_config()
    target = os.path.join(config, "custom_components", "homekit_architect")
    installed = os.path.isdir(target) and os.path.isfile(os.path.join(target, "manifest.json"))
    return {"config_dir": config, "target": target, "installed": installed, "source_exists": os.path.isdir(SOURCE)}


# ---------------------------------------------------------------------------
# HA API wrappers
# ---------------------------------------------------------------------------

def api_bridges():
    entries = ha_request("GET", "/config/config_entries/entry")
    if isinstance(entries, dict) and "error" in entries:
        return entries
    bridges = []
    for e in entries:
        if e.get("domain") != "homekit":
            continue
        opts = e.get("options") or {}
        if opts.get("homekit_mode") != "bridge":
            continue
        filt = opts.get("filter") or {}
        bridges.append({
            "entry_id": e["entry_id"],
            "title": e.get("title") or e.get("data", {}).get("name", "HomeKit Bridge"),
            "filter": {
                "include_entities": filt.get("include_entities") or [],
                "exclude_entities": filt.get("exclude_entities") or [],
                "include_domains": filt.get("include_domains") or [],
                "exclude_domains": filt.get("exclude_domains") or [],
            },
        })
    return {"bridges": bridges}


def api_bridge_entities(bridge_entry_id):
    br = api_bridges()
    if "error" in br:
        return br
    bridge = next((b for b in br["bridges"] if b["entry_id"] == bridge_entry_id), None)
    if not bridge:
        return {"error": "Bridge not found"}

    filt = bridge["filter"]
    inc_ent = set(filt["include_entities"])
    exc_ent = set(filt["exclude_entities"])
    inc_dom = set(filt["include_domains"])
    exc_dom = set(filt["exclude_domains"])

    states = ha_request("GET", "/states")
    if isinstance(states, dict) and "error" in states:
        return states

    entities = []
    for s in states:
        eid = s.get("entity_id", "")
        domain = eid.split(".")[0] if "." in eid else ""
        included = False
        if inc_ent and eid in inc_ent:
            included = True
        elif inc_dom and domain in inc_dom:
            included = True
        elif not inc_ent and not inc_dom:
            included = True
        if included and eid in exc_ent:
            included = False
        if included and domain in exc_dom:
            included = False
        if included:
            friendly = s.get("attributes", {}).get("friendly_name", eid)
            entities.append({
                "entity_id": eid,
                "domain": domain,
                "friendly_name": friendly,
                "state": s.get("state", ""),
            })
    entities.sort(key=lambda e: e["entity_id"])
    return {"entities": entities, "filter": filt}


def api_package(payload):
    atype = (payload.get("accessory_type") or "lock").lower()
    tmpl = {"lock": "security_lock", "cover": "garage_door"}.get(atype)
    if not tmpl:
        return {"error": f"Unknown accessory type: {atype}"}

    flow_data = {
        "template_id": tmpl,
        "slots": payload.get("slot_mapping") or {},
        "homekit_bridge_entry_id": payload.get("bridge_entry_id", ""),
        "automated_ghosting": payload.get("hide_sources", True),
        "friendly_name": (payload.get("display_name") or "Accessory").strip(),
    }

    result = ha_request("POST", "/config/config_entries/flow", {
        "handler": "homekit_architect",
        "show_advanced_options": False,
    })
    if isinstance(result, dict) and "error" in result:
        return result

    flow_id = result.get("flow_id")
    if not flow_id:
        return {"error": "Could not start config flow", "detail": result}

    step = result
    max_steps = 6
    for _ in range(max_steps):
        step_type = step.get("type")
        if step_type == "create_entry":
            return {"ok": True, "title": step.get("title", flow_data["friendly_name"]), "entry_id": step.get("result", {}).get("entry_id", "")}
        if step_type == "abort":
            return {"error": step.get("reason", "Flow aborted")}
        if step_type != "form":
            return {"error": f"Unexpected flow step type: {step_type}", "detail": step}

        step_id = step.get("step_id", "")
        if step_id == "user":
            step = ha_request("POST", f"/config/config_entries/flow/{flow_id}", {"template_id": tmpl})
        elif step_id == "slots":
            step = ha_request("POST", f"/config/config_entries/flow/{flow_id}", flow_data["slots"])
        elif step_id == "bridge":
            step = ha_request("POST", f"/config/config_entries/flow/{flow_id}", {"homekit_bridge_entry_id": flow_data["homekit_bridge_entry_id"]})
        elif step_id == "ghosting":
            step = ha_request("POST", f"/config/config_entries/flow/{flow_id}", {
                "automated_ghosting": flow_data["automated_ghosting"],
                "friendly_name": flow_data["friendly_name"],
            })
        elif step_id == "panel":
            step = ha_request("POST", f"/config/config_entries/flow/{flow_id}", flow_data)
        else:
            return {"error": f"Unknown flow step: {step_id}"}

        if isinstance(step, dict) and "error" in step:
            return step

    return {"error": "Config flow did not complete in expected steps"}


# ---------------------------------------------------------------------------
# HTML UI
# ---------------------------------------------------------------------------

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HomeKit Entity Architect</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#111;--card:#1c1c1c;--primary:#03a9f4;--error:#f44336;--success:#4caf50;--text:#e0e0e0;--muted:#888;--border:#333;--chip:#2a2a2a;--chip-active:#03a9f4}
body{font-family:Roboto,sans-serif;background:var(--bg);color:var(--text);padding:16px}
h1{font-size:22px;margin-bottom:4px}
h2{font-size:16px;margin-bottom:12px;font-weight:500}
.subtitle{color:var(--muted);font-size:13px;margin-bottom:20px}
.card{background:var(--card);border-radius:10px;padding:20px;margin-bottom:16px}
label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}
select,input[type=text]{width:100%;padding:10px 12px;font-size:14px;border-radius:6px;border:1px solid var(--border);background:#222;color:var(--text);margin-bottom:12px}
select:focus,input:focus{outline:none;border-color:var(--primary)}
.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:12px}
.toolbar input{max-width:220px;margin:0}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.chip{padding:5px 12px;border-radius:16px;font-size:12px;cursor:pointer;background:var(--chip);color:var(--text);border:1px solid transparent;user-select:none}
.chip.active{background:var(--chip-active);color:#fff;border-color:var(--primary)}
.entity-list{max-height:340px;overflow-y:auto;border:1px solid var(--border);border-radius:6px}
.entity-row{display:flex;align-items:center;gap:10px;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.06);cursor:pointer}
.entity-row:hover{background:rgba(255,255,255,.04)}
.entity-row input[type=checkbox]{flex-shrink:0}
.entity-row .name{flex:1;font-size:14px}
.entity-row .domain{font-size:11px;color:var(--muted);margin-right:6px}
.entity-row .state{font-size:12px;color:var(--muted)}
.btn{display:inline-block;padding:10px 22px;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;text-decoration:none;border:none;margin-right:8px;margin-top:8px}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover{opacity:.9}
.btn-primary:disabled{opacity:.4;cursor:not-allowed}
.btn-secondary{background:#333;color:var(--text)}
.msg{padding:10px;border-radius:6px;margin:12px 0;font-size:13px}
.msg.ok{background:rgba(76,175,80,.15);color:var(--success)}
.msg.err{background:rgba(244,67,54,.15);color:var(--error)}
.msg.warn{background:rgba(255,152,0,.15);color:#ff9800}
.loading{color:var(--muted);padding:12px}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:999}
.modal{background:var(--card);border-radius:12px;padding:24px;max-width:480px;width:92%;max-height:90vh;overflow-y:auto}
.modal h2{margin-bottom:16px}
.modal .field{margin-bottom:14px}
.modal .field label{margin-bottom:4px}
.modal .actions{margin-top:20px;display:flex;gap:10px;justify-content:flex-end}
.modal select.slot{width:100%;margin-top:4px}
.hr{border:none;border-top:1px solid var(--border);margin:16px 0}
.count{font-size:13px;color:var(--muted);margin-left:8px}
.select-all{font-size:13px;display:flex;align-items:center;gap:6px}
.status{font-size:13px;padding:10px 14px;border-radius:6px;background:rgba(0,0,0,.2)}
.status.ok{border-left:4px solid var(--success)}
.status.warn{border-left:4px solid #ff9800}
code{font-size:12px;background:#333;padding:2px 6px;border-radius:4px}
.hidden{display:none}
</style>
</head>
<body>
<h1>HomeKit Entity Architect</h1>
<p class="subtitle">Select a bridge, pick entities, and package them into a single HomeKit accessory.</p>

<!-- Bridge Selection -->
<div class="card" id="sec-bridge">
  <h2>A. Select HomeKit Bridge</h2>
  <label for="bridge-sel">Active bridges</label>
  <select id="bridge-sel"><option value="">Loading bridges…</option></select>
  <div id="bridge-filter" class="status hidden"></div>
</div>

<!-- Entity List -->
<div class="card hidden" id="sec-entities">
  <h2>B. Select Entities</h2>
  <div class="toolbar">
    <input type="text" id="search" placeholder="Search entities…">
    <label class="select-all"><input type="checkbox" id="select-all"> Select all</label>
    <button class="btn btn-primary" id="btn-package" disabled>Package as Accessory</button>
    <span class="count" id="sel-count"></span>
  </div>
  <div class="chips" id="chips"></div>
  <div class="entity-list" id="entity-list"></div>
  <div id="entity-msg"></div>
</div>

<!-- Messages -->
<div id="msg-area"></div>

<!-- Maintenance -->
<div class="card" style="margin-top:20px">
  <div id="install-status" class="status">Loading…</div>
  <div style="margin-top:12px">
    <button class="btn btn-secondary" id="btn-reinstall">Reinstall integration</button>
    <a href="/config/server_control" class="btn btn-secondary" target="_top">Restart Home Assistant</a>
  </div>
  <div id="install-msg"></div>
</div>

<!-- Package Modal (hidden) -->
<div class="modal-backdrop hidden" id="modal-bg">
<div class="modal">
  <h2>Package as Accessory</h2>
  <div class="field">
    <label>Display name</label>
    <input type="text" id="m-name" placeholder="e.g. Ventilation Fan">
  </div>
  <div class="field">
    <label>Accessory type</label>
    <select id="m-type">
      <option value="lock">Smart Lock</option>
      <option value="cover">Garage Door</option>
    </select>
  </div>
  <div class="field">
    <label><input type="checkbox" id="m-ghost" checked> Hide source entities from HomeKit (ghosting)</label>
  </div>
  <div class="field" id="m-slots"></div>
  <div class="actions">
    <button class="btn btn-secondary" id="m-cancel">Cancel</button>
    <button class="btn btn-primary" id="m-submit">Create</button>
  </div>
</div>
</div>

<script>
(function(){
  var base = document.location.pathname.replace(/\/?$/, '/');
  var bridges = [];
  var bridgeId = '';
  var entities = [];
  var selected = {};
  var search = '';
  var domainFilter = {};
  var SLOTS = {
    security_lock: {action_slot:'Lock actuator (switch/lock)', state_slot:'State sensor (e.g. door contact)', battery_slot:'Battery (optional)', obstruction_slot:'Obstruction/jam (optional)'},
    garage_door: {actuator_slot:'Open/Close actuator', position_sensor_slot:'Position sensor (door contact/cover)', battery_slot:'Battery (optional)'}
  };
  var TYPE_MAP = {lock:'security_lock', cover:'garage_door'};

  function $(id){return document.getElementById(id)}
  function esc(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
  function api(method, path, body){
    var opts = {method:method, headers:{'Content-Type':'application/json'}};
    if(body) opts.body = JSON.stringify(body);
    return fetch(base + path, opts).then(function(r){return r.json()});
  }

  // --- Bridge ---
  function loadBridges(){
    api('GET','api/bridges').then(function(d){
      if(d.error){$('bridge-sel').innerHTML='<option>Error: '+esc(d.error)+'</option>';return}
      bridges = d.bridges || [];
      var html = '<option value="">-- Select a bridge --</option>';
      bridges.forEach(function(b){html+='<option value="'+esc(b.entry_id)+'">'+esc(b.title)+'</option>'});
      $('bridge-sel').innerHTML = html;
    }).catch(function(){$('bridge-sel').innerHTML='<option>Could not load bridges</option>'});
  }

  $('bridge-sel').addEventListener('change', function(){
    bridgeId = this.value;
    entities = []; selected = {}; search = ''; domainFilter = {};
    $('search').value = '';
    if(!bridgeId){$('sec-entities').classList.add('hidden');$('bridge-filter').classList.add('hidden');return}
    var br = bridges.find(function(b){return b.entry_id===bridgeId});
    if(br && br.filter){
      var f=br.filter;
      $('bridge-filter').className='status ok';
      $('bridge-filter').innerHTML='Include: '+((f.include_entities||[]).length)+' entities, '+((f.include_domains||[]).length)+' domains &middot; Exclude: '+((f.exclude_entities||[]).length)+' entities, '+((f.exclude_domains||[]).length)+' domains';
    } else { $('bridge-filter').classList.add('hidden'); }
    loadEntities();
  });

  function loadEntities(){
    $('entity-list').innerHTML='<div class="loading">Loading entities…</div>';
    $('sec-entities').classList.remove('hidden');
    api('GET','api/entities?bridge_entry_id='+encodeURIComponent(bridgeId)).then(function(d){
      if(d.error){$('entity-list').innerHTML='<div class="msg err">'+esc(d.error)+'</div>';return}
      entities = d.entities || [];
      renderEntities();
    }).catch(function(){$('entity-list').innerHTML='<div class="msg err">Failed to load entities</div>'});
  }

  // --- Render ---
  function getFiltered(){
    var q = search.toLowerCase();
    var activeDomains = Object.keys(domainFilter).filter(function(k){return domainFilter[k]});
    return entities.filter(function(e){
      if(q && e.entity_id.toLowerCase().indexOf(q)===-1 && (e.friendly_name||'').toLowerCase().indexOf(q)===-1) return false;
      if(activeDomains.length && activeDomains.indexOf(e.domain)===-1) return false;
      return true;
    });
  }

  function renderEntities(){
    var filtered = getFiltered();
    var domains = {};
    entities.forEach(function(e){if(e.domain) domains[e.domain]=true});
    var sortedDomains = Object.keys(domains).sort();

    var chipHtml = '';
    sortedDomains.forEach(function(d){
      chipHtml+='<span class="chip'+(domainFilter[d]?' active':'')+'" data-domain="'+esc(d)+'">'+esc(d)+'</span>';
    });
    $('chips').innerHTML = chipHtml;
    $('chips').querySelectorAll('.chip').forEach(function(el){
      el.addEventListener('click', function(){
        var d=el.getAttribute('data-domain');
        domainFilter[d]=!domainFilter[d];
        renderEntities();
      });
    });

    var html = '';
    filtered.forEach(function(e){
      var chk = selected[e.entity_id] ? ' checked' : '';
      html+='<div class="entity-row" data-eid="'+esc(e.entity_id)+'"><input type="checkbox"'+chk+'><span class="name"><span class="domain">'+esc(e.domain)+'</span> '+esc(e.friendly_name||e.entity_id)+'</span><span class="state">'+esc(e.state)+'</span></div>';
    });
    if(!html) html='<div style="padding:12px;color:var(--muted)">No entities match your search or filter.</div>';
    $('entity-list').innerHTML = html;

    $('entity-list').querySelectorAll('.entity-row').forEach(function(row){
      var eid = row.getAttribute('data-eid');
      var cb = row.querySelector('input[type=checkbox]');
      function toggle(){selected[eid]=!selected[eid]; cb.checked=!!selected[eid]; updateCount()}
      cb.addEventListener('change', toggle);
      row.addEventListener('click', function(ev){if(ev.target!==cb){toggle()}});
    });

    updateCount();
    var allChecked = filtered.length>0 && filtered.every(function(e){return selected[e.entity_id]});
    $('select-all').checked = allChecked;
  }

  $('search').addEventListener('input', function(){search=this.value;renderEntities()});
  $('select-all').addEventListener('change', function(){
    var checked = this.checked;
    getFiltered().forEach(function(e){selected[e.entity_id]=checked});
    renderEntities();
  });

  function updateCount(){
    var count = Object.keys(selected).filter(function(k){return selected[k]}).length;
    $('sel-count').textContent = count ? count + ' selected' : '';
    $('btn-package').disabled = count===0;
  }

  // --- Package Modal ---
  $('btn-package').addEventListener('click', openModal);
  $('m-cancel').addEventListener('click', closeModal);
  $('modal-bg').addEventListener('click', function(e){if(e.target===$('modal-bg')) closeModal()});
  $('m-type').addEventListener('change', renderSlots);

  function getSelectedIds(){return Object.keys(selected).filter(function(k){return selected[k]})}

  function openModal(){
    $('m-name').value='';
    $('m-type').value='lock';
    $('m-ghost').checked=true;
    $('modal-bg').classList.remove('hidden');
    renderSlots();
  }
  function closeModal(){$('modal-bg').classList.add('hidden')}

  function renderSlots(){
    var tmpl = TYPE_MAP[$('m-type').value] || 'security_lock';
    var slots = SLOTS[tmpl] || {};
    var ids = getSelectedIds();
    var html='<label>Slot mapping (assign entities to roles)</label>';
    Object.keys(slots).forEach(function(key){
      html+='<div style="margin-bottom:8px"><span style="font-size:12px;color:var(--muted)">'+esc(slots[key])+'</span><select class="slot" data-slot="'+esc(key)+'">';
      html+='<option value="">--</option>';
      ids.forEach(function(eid){html+='<option value="'+esc(eid)+'">'+esc(eid)+'</option>'});
      html+='</select></div>';
    });
    $('m-slots').innerHTML=html;
    suggestSlots(tmpl, ids);
  }

  function suggestSlots(tmpl, ids){
    var byDomain={};
    ids.forEach(function(eid){var d=eid.split('.')[0];if(!byDomain[d])byDomain[d]=[];byDomain[d].push(eid)});
    var selects = $('m-slots').querySelectorAll('select.slot');
    selects.forEach(function(sel){
      var slot=sel.getAttribute('data-slot');
      var v='';
      if(tmpl==='security_lock'){
        if(slot==='action_slot') v=(byDomain.lock||[])[0]||(byDomain.switch||[])[0]||ids[0]||'';
        if(slot==='state_slot') v=(byDomain.binary_sensor||[])[0]||ids[1]||ids[0]||'';
        if(slot==='battery_slot') v=(byDomain.sensor||[])[0]||'';
        if(slot==='obstruction_slot') v=(byDomain.binary_sensor||[])[1]||'';
      } else {
        if(slot==='actuator_slot') v=(byDomain.cover||[])[0]||(byDomain.switch||[])[0]||ids[0]||'';
        if(slot==='position_sensor_slot') v=(byDomain.binary_sensor||[])[0]||(byDomain.cover||[])[0]||ids[1]||ids[0]||'';
        if(slot==='battery_slot') v=(byDomain.sensor||[])[0]||'';
      }
      if(v) sel.value=v;
    });
  }

  $('m-submit').addEventListener('click', function(){
    var btn=$('m-submit');
    btn.disabled=true; btn.textContent='Creating…';
    var slotMapping={};
    $('m-slots').querySelectorAll('select.slot').forEach(function(sel){
      var k=sel.getAttribute('data-slot'), v=sel.value;
      if(k&&v) slotMapping[k]=v;
    });
    api('POST','api/package',{
      bridge_entry_id: bridgeId,
      display_name: $('m-name').value || 'Accessory',
      accessory_type: $('m-type').value,
      entity_ids: getSelectedIds(),
      slot_mapping: slotMapping,
      hide_sources: $('m-ghost').checked
    }).then(function(d){
      btn.disabled=false; btn.textContent='Create';
      if(d.ok){
        closeModal();
        selected={};
        renderEntities();
        showMsg('msg-area','Created "'+esc(d.title||'Accessory')+'". The virtual entity will appear after HA processes the new config entry.','ok');
      } else {
        showMsg('msg-area', d.error || 'Package failed.', 'err');
      }
    }).catch(function(){btn.disabled=false;btn.textContent='Create';showMsg('msg-area','Request failed','err')});
  });

  function showMsg(id, text, cls){
    $(id).innerHTML='<div class="msg '+cls+'">'+text+'</div>';
    setTimeout(function(){$(id).innerHTML=''},8000);
  }

  // --- Maintenance ---
  function loadStatus(){
    api('GET','status').then(function(d){
      if(d.installed){$('install-status').className='status ok';$('install-status').innerHTML='Integration installed at <code>'+esc(d.target)+'</code>'}
      else if(d.source_exists){$('install-status').className='status warn';$('install-status').innerHTML='Not installed. Click "Reinstall integration".'}
      else{$('install-status').className='status';$('install-status').textContent='Source not found. Rebuild the app.'}
    }).catch(function(){$('install-status').textContent='Could not load status.'});
  }
  $('btn-reinstall').addEventListener('click', function(){
    var btn=$('btn-reinstall'); btn.disabled=true;
    api('POST','reinstall').then(function(d){
      btn.disabled=false;
      showMsg('install-msg', d.ok ? (d.message||'Reinstalled. Restart HA to load changes.') : (d.error||'Failed'), d.ok?'ok':'err');
      loadStatus();
    }).catch(function(){btn.disabled=false;showMsg('install-msg','Request failed','err')});
  });

  // --- Init ---
  loadBridges();
  loadStatus();
})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[server] " + fmt % args + "\n")

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode()) if length else {}

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/" or path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
            return

        if path == "/status":
            self._json(200, get_status())
            return

        if path == "/api/bridges":
            self._json(200, api_bridges())
            return

        if path.startswith("/api/entities"):
            qs = urlparse(self.path).query
            params = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
            bid = urllib.parse.unquote(params.get("bridge_entry_id", ""))
            if not bid:
                self._json(400, {"error": "bridge_entry_id required"})
            else:
                self._json(200, api_bridge_entities(bid))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/reinstall":
            try:
                target = run_install()
                self._json(200, {"ok": True, "message": f"Integration installed to {target}. Restart HA to load."})
            except Exception as e:
                self._json(200, {"ok": False, "error": str(e)})
            return

        if path == "/api/package":
            body = self._read_body()
            self._json(200, api_package(body))
            return

        self.send_response(404)
        self.end_headers()


def main():
    server = HTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    sys.stderr.write(f"[HomeKit Entity Architect] Web UI listening on port {LISTEN_PORT}\n")
    server.serve_forever()


if __name__ == "__main__":
    main()
