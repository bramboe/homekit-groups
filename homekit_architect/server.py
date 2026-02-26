#!/usr/bin/env python3
"""
HomeKit Entity Architect – Ingress UI.
Serves the full configuration screen: bridge selection, entity discovery,
functional packaging, and automated ghosting.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

LISTEN_PORT = 8099
HA_API = "http://supervisor/core/api"
HA_DIRECT = None  # set if using a long-lived token (direct to HA, not via supervisor)


def _read_options():
    try:
        with open("/data/options.json") as f:
            return json.load(f)
    except Exception:
        return {}


def _token():
    # 1. Supervisor token (set when homeassistant_api:true was present at install)
    t = os.environ.get("SUPERVISOR_TOKEN", "")
    if t:
        return t, HA_API
    # 2. Long-lived access token from add-on options (fallback)
    opts = _read_options()
    t = (opts.get("ha_token") or "").strip()
    if t:
        return t, "http://supervisor/core/api"
    return "", HA_API


def ha(method, path, data=None):
    token, base = _token()
    url = f"{base}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        sys.stderr.write(f"[ha] {method} {path} → {e.code}: {detail}\n")
        return {"error": f"{e.code}: {detail}"}
    except Exception as e:
        sys.stderr.write(f"[ha] {method} {path} → {e}\n")
        return {"error": str(e)}


# -- API handlers ----------------------------------------------------------

def api_bridges():
    entries = ha("GET", "/config/config_entries/entry")
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


def api_entities(bridge_entry_id):
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

    states = ha("GET", "/states")
    if isinstance(states, dict) and "error" in states:
        return states

    out = []
    for s in states:
        eid = s.get("entity_id", "")
        dom = eid.split(".")[0] if "." in eid else ""
        ok = False
        if inc_ent and eid in inc_ent:
            ok = True
        elif inc_dom and dom in inc_dom:
            ok = True
        elif not inc_ent and not inc_dom:
            ok = True
        if ok and (eid in exc_ent or dom in exc_dom):
            ok = False
        if ok:
            out.append({
                "entity_id": eid,
                "domain": dom,
                "friendly_name": s.get("attributes", {}).get("friendly_name", eid),
                "state": s.get("state", ""),
            })
    out.sort(key=lambda e: e["entity_id"])
    return {"entities": out, "filter": filt}


def api_package(payload):
    atype = (payload.get("accessory_type") or "lock").lower()
    tmpl = {"lock": "security_lock", "cover": "garage_door"}.get(atype)
    if not tmpl:
        return {"error": f"Unknown type: {atype}"}

    flow_data = {
        "template_id": tmpl,
        "slots": payload.get("slot_mapping") or {},
        "homekit_bridge_entry_id": payload.get("bridge_entry_id", ""),
        "automated_ghosting": payload.get("hide_sources", True),
        "friendly_name": (payload.get("display_name") or "Accessory").strip(),
    }

    step = ha("POST", "/config/config_entries/flow", {
        "handler": "homekit_architect",
        "show_advanced_options": False,
    })
    if isinstance(step, dict) and "error" in step:
        return step
    flow_id = step.get("flow_id")
    if not flow_id:
        return {"error": "Could not start config flow"}

    for _ in range(6):
        t = step.get("type")
        if t == "create_entry":
            return {"ok": True, "title": step.get("title", flow_data["friendly_name"])}
        if t == "abort":
            return {"error": step.get("reason", "Aborted")}
        if t != "form":
            return {"error": f"Unexpected step type: {t}"}
        sid = step.get("step_id", "")
        if sid == "user":
            step = ha("POST", f"/config/config_entries/flow/{flow_id}", {"template_id": tmpl})
        elif sid == "slots":
            step = ha("POST", f"/config/config_entries/flow/{flow_id}", flow_data["slots"])
        elif sid == "bridge":
            step = ha("POST", f"/config/config_entries/flow/{flow_id}", {"homekit_bridge_entry_id": flow_data["homekit_bridge_entry_id"]})
        elif sid == "ghosting":
            step = ha("POST", f"/config/config_entries/flow/{flow_id}", {"automated_ghosting": flow_data["automated_ghosting"], "friendly_name": flow_data["friendly_name"]})
        elif sid == "panel":
            step = ha("POST", f"/config/config_entries/flow/{flow_id}", flow_data)
        else:
            return {"error": f"Unknown step: {sid}"}
        if isinstance(step, dict) and "error" in step:
            return step
    return {"error": "Flow did not complete"}


# -- HTML ------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HomeKit Architect</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#111;--card:#1c1c1c;--pri:#03a9f4;--err:#f44336;--ok:#4caf50;--txt:#e0e0e0;--dim:#888;--bdr:#333;--chip:#2a2a2a}
body{font-family:Roboto,sans-serif;background:var(--bg);color:var(--txt);padding:20px;max-width:720px;margin:0 auto}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--dim);font-size:13px;margin-bottom:20px}
.card{background:var(--card);border-radius:10px;padding:20px;margin-bottom:16px}
.card h2{font-size:15px;font-weight:500;margin-bottom:14px;color:var(--dim)}
label.field{display:block;font-size:13px;color:var(--dim);margin-bottom:6px}
select,input[type=text]{width:100%;padding:10px 12px;font-size:14px;border-radius:6px;border:1px solid var(--bdr);background:#222;color:var(--txt);margin-bottom:4px;outline:none}
select:focus,input:focus{border-color:var(--pri)}
.bar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:10px}
.bar input[type=text]{max-width:240px;margin:0}
.bar .sa{font-size:13px;display:flex;align-items:center;gap:5px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.chip{padding:4px 12px;border-radius:16px;font-size:12px;cursor:pointer;background:var(--chip);user-select:none}
.chip.on{background:var(--pri);color:#fff}
.elist{max-height:360px;overflow-y:auto;border:1px solid var(--bdr);border-radius:6px}
.erow{display:flex;align-items:center;gap:10px;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.05);cursor:pointer}
.erow:hover{background:rgba(255,255,255,.04)}
.erow .nm{flex:1;font-size:14px}.erow .dm{font-size:11px;color:var(--dim);margin-right:6px}.erow .st{font-size:12px;color:var(--dim)}
.btn{display:inline-block;padding:10px 22px;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;border:none}
.bp{background:var(--pri);color:#fff}.bp:disabled{opacity:.35;cursor:default}
.bs{background:#333;color:var(--txt)}
.msg{padding:10px;border-radius:6px;margin:10px 0;font-size:13px}
.msg.ok{background:rgba(76,175,80,.15);color:var(--ok)}
.msg.err{background:rgba(244,67,54,.15);color:var(--err)}
.cnt{font-size:13px;color:var(--dim);margin-left:6px}
.none{padding:14px;color:var(--dim);font-size:13px}
.mbg{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:999}
.mdl{background:var(--card);border-radius:12px;padding:24px;max-width:480px;width:92%;max-height:90vh;overflow-y:auto}
.mdl h2{font-size:18px;margin-bottom:16px}
.mdl .f{margin-bottom:14px}
.mdl .f label{display:block;font-size:12px;color:var(--dim);margin-bottom:4px}
.mdl .f select.sl{width:100%;margin-top:4px}
.mdl .acts{margin-top:20px;display:flex;gap:10px;justify-content:flex-end}
.hide{display:none}
</style>
</head>
<body>
<h1>HomeKit Architect</h1>
<p class="sub">Select a bridge, pick entities, and package them into a single HomeKit accessory.</p>

<div class="card">
  <h2>Bridge</h2>
  <label class="field">Active HomeKit bridges</label>
  <select id="bsel"><option value="">Loading…</option></select>
</div>

<div class="card hide" id="epanel">
  <h2>Entities</h2>
  <div class="bar">
    <input type="text" id="q" placeholder="Search…">
    <label class="sa"><input type="checkbox" id="sa"> All</label>
    <button class="btn bp" id="pkg" disabled>Package as Accessory</button>
    <span class="cnt" id="cnt"></span>
  </div>
  <div class="chips" id="chips"></div>
  <div class="elist" id="elist"></div>
</div>

<div id="toast"></div>

<div class="mbg hide" id="mbg">
<div class="mdl">
  <h2>Package as Accessory</h2>
  <div class="f"><label>Display name</label><input type="text" id="mn" placeholder="e.g. Ventilation Fan"></div>
  <div class="f"><label>Accessory type</label><select id="mt"><option value="lock">Smart Lock</option><option value="cover">Garage Door</option></select></div>
  <div class="f"><label><input type="checkbox" id="mg" checked> Hide source entities from HomeKit</label></div>
  <div class="f" id="ms"></div>
  <div class="acts"><button class="btn bs" id="mc">Cancel</button><button class="btn bp" id="mk">Create</button></div>
</div>
</div>

<script>
(function(){
var B=document.location.pathname.replace(/\/?$/,'/');
var bridges=[],bid='',ents=[],sel={},q='',df={};
var SLOTS={
  security_lock:{action_slot:'Lock actuator',state_slot:'State sensor',battery_slot:'Battery (optional)',obstruction_slot:'Obstruction (optional)'},
  garage_door:{actuator_slot:'Open/Close actuator',position_sensor_slot:'Position sensor',battery_slot:'Battery (optional)'}
};
var TM={lock:'security_lock',cover:'garage_door'};
function $(i){return document.getElementById(i)}
function esc(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
function api(m,p,b){var o={method:m,headers:{'Content-Type':'application/json'}};if(b)o.body=JSON.stringify(b);return fetch(B+p,o).then(function(r){return r.json()})}

// Bridge
function loadBridges(){
  api('GET','api/bridges').then(function(d){
    if(d.error){$('bsel').innerHTML='<option>'+esc(d.error)+'</option>';return}
    bridges=d.bridges||[];
    var h='<option value="">Select a bridge…</option>';
    bridges.forEach(function(b){h+='<option value="'+esc(b.entry_id)+'">'+esc(b.title)+'</option>'});
    $('bsel').innerHTML=h;
  }).catch(function(e){$('bsel').innerHTML='<option>Failed to load</option>'});
}
$('bsel').addEventListener('change',function(){
  bid=this.value;ents=[];sel={};q='';df={};$('q').value='';
  if(!bid){$('epanel').classList.add('hide');return}
  loadEnts();
});
function loadEnts(){
  $('elist').innerHTML='<div class="none">Loading…</div>';
  $('epanel').classList.remove('hide');
  api('GET','api/entities?bridge_entry_id='+encodeURIComponent(bid)).then(function(d){
    if(d.error){$('elist').innerHTML='<div class="msg err">'+esc(d.error)+'</div>';return}
    ents=d.entities||[];render();
  }).catch(function(){$('elist').innerHTML='<div class="msg err">Failed</div>'});
}

// Render
function filt(){
  var s=q.toLowerCase(),ad=Object.keys(df).filter(function(k){return df[k]});
  return ents.filter(function(e){
    if(s&&e.entity_id.toLowerCase().indexOf(s)<0&&(e.friendly_name||'').toLowerCase().indexOf(s)<0)return false;
    if(ad.length&&ad.indexOf(e.domain)<0)return false;return true;
  });
}
function render(){
  var f=filt(),doms={};
  ents.forEach(function(e){if(e.domain)doms[e.domain]=true});
  var ch='';Object.keys(doms).sort().forEach(function(d){ch+='<span class="chip'+(df[d]?' on':'')+'" data-d="'+esc(d)+'">'+esc(d)+'</span>'});
  $('chips').innerHTML=ch;
  $('chips').querySelectorAll('.chip').forEach(function(el){el.addEventListener('click',function(){df[el.getAttribute('data-d')]=!df[el.getAttribute('data-d')];render()})});
  var h='';
  f.forEach(function(e){
    h+='<div class="erow" data-e="'+esc(e.entity_id)+'"><input type="checkbox"'+(sel[e.entity_id]?' checked':'')+'><span class="nm"><span class="dm">'+esc(e.domain)+'</span>'+esc(e.friendly_name||e.entity_id)+'</span><span class="st">'+esc(e.state)+'</span></div>';
  });
  if(!h)h='<div class="none">No entities match.</div>';
  $('elist').innerHTML=h;
  $('elist').querySelectorAll('.erow').forEach(function(r){
    var id=r.getAttribute('data-e'),cb=r.querySelector('input');
    function t(){sel[id]=!sel[id];cb.checked=!!sel[id];upd()}
    cb.addEventListener('change',t);r.addEventListener('click',function(ev){if(ev.target!==cb)t()});
  });
  upd();
  $('sa').checked=f.length>0&&f.every(function(e){return sel[e.entity_id]});
}
$('q').addEventListener('input',function(){q=this.value;render()});
$('sa').addEventListener('change',function(){var c=this.checked;filt().forEach(function(e){sel[e.entity_id]=c});render()});
function upd(){var n=Object.keys(sel).filter(function(k){return sel[k]}).length;$('cnt').textContent=n?n+' selected':'';$('pkg').disabled=n===0}
function ids(){return Object.keys(sel).filter(function(k){return sel[k]})}

// Modal
$('pkg').addEventListener('click',function(){$('mn').value='';$('mt').value='lock';$('mg').checked=true;$('mbg').classList.remove('hide');rslots()});
$('mc').addEventListener('click',cm);$('mbg').addEventListener('click',function(e){if(e.target===$('mbg'))cm()});
$('mt').addEventListener('change',rslots);
function cm(){$('mbg').classList.add('hide')}
function rslots(){
  var t=TM[$('mt').value]||'security_lock',sl=SLOTS[t]||{},i=ids();
  var h='<label style="font-size:12px;color:var(--dim)">Slot mapping</label>';
  Object.keys(sl).forEach(function(k){
    h+='<div style="margin:6px 0"><span style="font-size:12px;color:var(--dim)">'+esc(sl[k])+'</span><select class="sl" data-s="'+esc(k)+'"><option value="">--</option>';
    i.forEach(function(e){h+='<option value="'+esc(e)+'">'+esc(e)+'</option>'});h+='</select></div>';
  });
  $('ms').innerHTML=h;suggest(t,i);
}
function suggest(t,i){
  var bd={};i.forEach(function(e){var d=e.split('.')[0];if(!bd[d])bd[d]=[];bd[d].push(e)});
  $('ms').querySelectorAll('select.sl').forEach(function(s){
    var k=s.getAttribute('data-s'),v='';
    if(t==='security_lock'){
      if(k==='action_slot')v=(bd.lock||[])[0]||(bd.switch||[])[0]||i[0]||'';
      if(k==='state_slot')v=(bd.binary_sensor||[])[0]||i[1]||i[0]||'';
      if(k==='battery_slot')v=(bd.sensor||[])[0]||'';
      if(k==='obstruction_slot')v=(bd.binary_sensor||[])[1]||'';
    }else{
      if(k==='actuator_slot')v=(bd.cover||[])[0]||(bd.switch||[])[0]||i[0]||'';
      if(k==='position_sensor_slot')v=(bd.binary_sensor||[])[0]||(bd.cover||[])[0]||i[1]||i[0]||'';
      if(k==='battery_slot')v=(bd.sensor||[])[0]||'';
    }
    if(v)s.value=v;
  });
}
$('mk').addEventListener('click',function(){
  var btn=$('mk');btn.disabled=true;btn.textContent='Creating…';
  var sm={};$('ms').querySelectorAll('select.sl').forEach(function(s){var k=s.getAttribute('data-s');if(k&&s.value)sm[k]=s.value});
  api('POST','api/package',{bridge_entry_id:bid,display_name:$('mn').value||'Accessory',accessory_type:$('mt').value,entity_ids:ids(),slot_mapping:sm,hide_sources:$('mg').checked})
  .then(function(d){
    btn.disabled=false;btn.textContent='Create';
    if(d.ok){cm();sel={};render();toast('Created "'+esc(d.title)+'"','ok')}
    else toast(d.error||'Failed','err');
  }).catch(function(){btn.disabled=false;btn.textContent='Create';toast('Request failed','err')});
});

function toast(t,c){$('toast').innerHTML='<div class="msg '+c+'">'+t+'</div>';setTimeout(function(){$('toast').innerHTML=''},6000)}

loadBridges();
})();
</script>
</body>
</html>
"""


# -- HTTP handler ----------------------------------------------------------

class H(BaseHTTPRequestHandler):
    def log_message(self, f, *a):
        sys.stderr.write("[server] " + f % a + "\n")

    def _j(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n).decode()) if n else {}

    def do_GET(self):
        p = urlparse(self.path).path.rstrip("/") or "/"
        if p == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())
            return
        if p == "/api/bridges":
            self._j(200, api_bridges())
            return
        if p.startswith("/api/entities"):
            qs = urlparse(self.path).query
            params = dict(x.split("=", 1) for x in qs.split("&") if "=" in x)
            bid = urllib.parse.unquote(params.get("bridge_entry_id", ""))
            self._j(200 if bid else 400, api_entities(bid) if bid else {"error": "bridge_entry_id required"})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        p = urlparse(self.path).path.rstrip("/") or "/"
        if p == "/api/package":
            self._j(200, api_package(self._body()))
            return
        self.send_response(404)
        self.end_headers()


def main():
    token, base = _token()
    source = "SUPERVISOR_TOKEN" if os.environ.get("SUPERVISOR_TOKEN") else ("ha_token option" if token else "none")
    sys.stderr.write(f"[HomeKit Architect] Auth: {source} (token len={len(token)})\n")
    HTTPServer(("0.0.0.0", LISTEN_PORT), H).serve_forever()


if __name__ == "__main__":
    main()
