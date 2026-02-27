#!/usr/bin/env python3
"""
HomeKit Entity Architect – Ingress UI server.
Serves the HTML/JS page.  All HA API calls happen browser-side using the auth
token the HA frontend already stores in localStorage (same origin).
"""
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

LISTEN_PORT = 8099

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
<div id="dbg" style="margin-top:32px;font-size:11px;color:#555;font-family:monospace"></div>

<div class="mbg hide" id="mbg">
<div class="mdl">
  <h2>Package as Accessory</h2>
  <div class="f"><label>Display name</label><input type="text" id="mn" placeholder="e.g. Ventilation Fan"></div>
  <div class="f"><label>Accessory type</label><select id="mt">
    <optgroup label="Security &amp; Access">
      <option value="lock">Door Lock</option>
      <option value="security_system">Security System</option>
      <option value="doorbell">Video Doorbell</option>
    </optgroup>
    <optgroup label="Doors, Gates &amp; Covers">
      <option value="garage_door">Garage Door</option>
      <option value="door">Door</option>
      <option value="window">Window</option>
      <option value="window_covering">Window Covering</option>
    </optgroup>
    <optgroup label="Lighting &amp; Power">
      <option value="lightbulb">Light</option>
      <option value="outlet">Outlet</option>
      <option value="switch">Switch</option>
    </optgroup>
    <optgroup label="Climate &amp; Environment">
      <option value="thermostat">Thermostat</option>
      <option value="fan">Fan</option>
      <option value="air_purifier">Air Purifier</option>
      <option value="humidifier">Humidifier</option>
      <option value="dehumidifier">Dehumidifier</option>
    </optgroup>
    <optgroup label="Water">
      <option value="sprinkler">Sprinkler</option>
      <option value="faucet">Faucet</option>
      <option value="shower">Shower Head</option>
    </optgroup>
    <optgroup label="Media">
      <option value="television">Television</option>
      <option value="speaker">Speaker</option>
    </optgroup>
    <optgroup label="Sensors">
      <option value="sensor">Sensor</option>
    </optgroup>
    <optgroup label="Other">
      <option value="camera">IP Camera</option>
      <option value="programmable_switch">Programmable Switch</option>
    </optgroup>
  </select></div>
  <div class="f"><label><input type="checkbox" id="mg" checked> Hide source entities from HomeKit</label></div>
  <div class="f" id="ms"></div>
  <div class="acts"><button class="btn bs" id="mc">Cancel</button><button class="btn bp" id="mk">Create</button></div>
</div>
</div>

<script>
(function(){

/* ── Auth ───────────────────────────────────────────────────────────
   The ingress iframe is served from the same origin as HA, so
   localStorage (where the HA frontend stores its auth token) is
   directly accessible.  No server-side token needed.
   ────────────────────────────────────────────────────────────────── */
var _td;
function tokenData(){
  if(!_td){try{_td=JSON.parse(localStorage.getItem('hassTokens'))}catch(e){}}
  return _td;
}

function getToken(){
  return new Promise(function(ok,fail){
    var d=tokenData();
    if(!d||!d.access_token){fail(new Error('No HA session found – refresh the page'));return}
    if(d.token_expires && Date.now()>d.token_expires){
      fetch('/auth/token',{
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:'grant_type=refresh_token&refresh_token='+encodeURIComponent(d.refresh_token)
            +'&client_id='+encodeURIComponent(d.clientId||'')
      })
      .then(function(r){if(!r.ok)throw new Error(r.status);return r.json()})
      .then(function(j){d.access_token=j.access_token;d.token_expires=Date.now()+j.expires_in*1000;localStorage.setItem('hassTokens',JSON.stringify(d));ok(j.access_token)})
      .catch(fail);
    }else{ok(d.access_token)}
  });
}

function handleResp(r){
  if(r.ok) return r.json();
  return r.text().then(function(body){
    var detail=body;
    try{var j=JSON.parse(body);detail=j.message||j.error||j.detail||body}catch(e){}
    throw new Error(r.status+' '+r.statusText+': '+detail);
  });
}

function haGet(path){
  return getToken().then(function(t){
    return fetch('/api'+path,{headers:{'Authorization':'Bearer '+t}});
  }).then(handleResp);
}
function haPost(path,body){
  return getToken().then(function(t){
    return fetch('/api'+path,{method:'POST',headers:{'Authorization':'Bearer '+t,'Content-Type':'application/json'},body:JSON.stringify(body)});
  }).then(handleResp);
}

/* ── Helpers ──── */
var bridges=[],bid='',ents=[],sel={},q='',df={};
var SLOTS={
  lock:          {action_slot:'Lock actuator',state_slot:'State sensor',battery_slot:'Battery (optional)',obstruction_slot:'Obstruction (optional)'},
  security_system:{arm_slot:'Arm/Disarm control',state_slot:'State sensor',battery_slot:'Battery (optional)'},
  doorbell:      {trigger_slot:'Doorbell trigger',camera_slot:'Camera stream (optional)',battery_slot:'Battery (optional)'},
  garage_door:   {actuator_slot:'Open/Close actuator',position_sensor_slot:'Position sensor',obstruction_slot:'Obstruction (optional)',battery_slot:'Battery (optional)'},
  door:          {actuator_slot:'Open/Close actuator',position_sensor_slot:'Position sensor',battery_slot:'Battery (optional)'},
  window:        {actuator_slot:'Open/Close actuator',position_sensor_slot:'Position sensor',battery_slot:'Battery (optional)'},
  window_covering:{position_slot:'Position control',tilt_slot:'Tilt control (optional)',battery_slot:'Battery (optional)'},
  lightbulb:     {switch_slot:'On/Off control',brightness_slot:'Brightness (optional)',color_slot:'Color (optional)'},
  outlet:        {switch_slot:'On/Off control',power_sensor_slot:'Power sensor (optional)'},
  switch:        {switch_slot:'On/Off control',state_slot:'State sensor (optional)'},
  thermostat:    {climate_slot:'Climate entity',temperature_sensor_slot:'Temperature sensor (optional)',humidity_sensor_slot:'Humidity sensor (optional)'},
  fan:           {switch_slot:'On/Off control',speed_slot:'Speed control (optional)',battery_slot:'Battery (optional)'},
  air_purifier:  {switch_slot:'On/Off control',air_quality_slot:'Air quality sensor (optional)',filter_slot:'Filter life (optional)'},
  humidifier:    {switch_slot:'On/Off control',humidity_sensor_slot:'Humidity sensor (optional)',target_slot:'Target humidity (optional)'},
  dehumidifier:  {switch_slot:'On/Off control',humidity_sensor_slot:'Humidity sensor (optional)',target_slot:'Target humidity (optional)'},
  sprinkler:     {switch_slot:'On/Off control',timer_slot:'Timer/Duration (optional)'},
  faucet:        {switch_slot:'On/Off control'},
  shower:        {switch_slot:'On/Off control'},
  television:    {media_slot:'Media player entity',power_slot:'Power control (optional)'},
  speaker:       {media_slot:'Media player entity',volume_slot:'Volume control (optional)'},
  sensor:        {primary_slot:'Primary sensor',secondary_slot:'Secondary sensor (optional)',battery_slot:'Battery (optional)'},
  camera:        {camera_slot:'Camera entity',motion_slot:'Motion sensor (optional)'},
  programmable_switch:{trigger_slot:'Trigger entity',battery_slot:'Battery (optional)'}
};

function $(i){return document.getElementById(i)}
function esc(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML}

/* ── Bridges ──── */
function loadBridges(){
  haGet('/config/config_entries/entry').then(function(entries){
    bridges=[];
    entries.forEach(function(e){
      if(e.domain!=='homekit')return;
      var opts=e.options||{};
      var data=e.data||{};
      var mode=opts.homekit_mode||data.homekit_mode||'bridge';
      if(mode==='accessory')return;
      var f=opts.filter||data.filter||{};
      bridges.push({entry_id:e.entry_id,title:e.title||'HomeKit Bridge',filter:{
        include_entities:f.include_entities||[],exclude_entities:f.exclude_entities||[],
        include_domains:f.include_domains||[],exclude_domains:f.exclude_domains||[]
      }});
    });
    var h='<option value="">Select a bridge…</option>';
    bridges.forEach(function(b){h+='<option value="'+esc(b.entry_id)+'">'+esc(b.title)+'</option>'});
    if(!bridges.length)h='<option value="">No HomeKit bridges found</option>';
    $('bsel').innerHTML=h;
  }).catch(function(e){$('bsel').innerHTML='<option>Error: '+esc(String(e))+'</option>'});
}

$('bsel').addEventListener('change',function(){
  bid=this.value;ents=[];sel={};q='';df={};$('q').value='';
  if(!bid){$('epanel').classList.add('hide');return}
  loadEnts();
});

/* ── Entities ── */
function loadEnts(){
  $('elist').innerHTML='<div class="none">Loading…</div>';
  $('epanel').classList.remove('hide');
  var br=bridges.find(function(b){return b.entry_id===bid});
  if(!br){$('elist').innerHTML='<div class="msg err">Bridge not found</div>';return}

  haGet('/states').then(function(states){
    var f=br.filter;
    var incE=new Set(f.include_entities),excE=new Set(f.exclude_entities);
    var incD=new Set(f.include_domains),excD=new Set(f.exclude_domains);
    ents=[];
    states.forEach(function(s){
      var eid=s.entity_id||'',dom=eid.split('.')[0]||'';
      var ok=false;
      if(incE.size&&incE.has(eid))ok=true;
      else if(incD.size&&incD.has(dom))ok=true;
      else if(!incE.size&&!incD.size)ok=true;
      if(ok&&(excE.has(eid)||excD.has(dom)))ok=false;
      if(ok)ents.push({entity_id:eid,domain:dom,friendly_name:(s.attributes||{}).friendly_name||eid,state:s.state||''});
    });
    ents.sort(function(a,b){return a.entity_id<b.entity_id?-1:1});
    render();
  }).catch(function(e){$('elist').innerHTML='<div class="msg err">'+esc(String(e))+'</div>'});
}

/* ── Render ── */
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

/* ── Package modal ── */
$('pkg').addEventListener('click',function(){$('mn').value='';$('mt').value='lock';$('mg').checked=true;$('mbg').classList.remove('hide');rslots()});
$('mc').addEventListener('click',cm);$('mbg').addEventListener('click',function(e){if(e.target===$('mbg'))cm()});
$('mt').addEventListener('change',rslots);
function cm(){$('mbg').classList.add('hide')}

function rslots(){
  var t=$('mt').value,sl=SLOTS[t]||{},i=ids();
  var keys=Object.keys(sl);
  if(!keys.length){$('ms').innerHTML='<span style="font-size:12px;color:var(--dim)">No slot mapping needed for this type.</span>';return}
  var h='<label style="font-size:12px;color:var(--dim)">Slot mapping</label>';
  keys.forEach(function(k){
    h+='<div style="margin:6px 0"><span style="font-size:12px;color:var(--dim)">'+esc(sl[k])+'</span><select class="sl" data-s="'+esc(k)+'"><option value="">--</option>';
    i.forEach(function(e){h+='<option value="'+esc(e)+'">'+esc(e)+'</option>'});h+='</select></div>';
  });
  $('ms').innerHTML=h;suggest(t,i);
}

function suggest(t,i){
  var bd={};i.forEach(function(e){var d=e.split('.')[0];if(!bd[d])bd[d]=[];bd[d].push(e)});
  var first=function(){return i[0]||''};
  var fromDom=function(doms){for(var x=0;x<doms.length;x++){var r=bd[doms[x]];if(r&&r.length)return r[0]}return ''};
  var hints={
    action_slot:       function(){return fromDom(['lock','switch'])||first()},
    arm_slot:          function(){return fromDom(['alarm_control_panel','switch'])||first()},
    trigger_slot:      function(){return fromDom(['binary_sensor','input_boolean','switch'])||first()},
    actuator_slot:     function(){return fromDom(['cover','switch'])||first()},
    switch_slot:       function(){return fromDom(['switch','light','fan','input_boolean'])||first()},
    climate_slot:      function(){return fromDom(['climate'])||first()},
    media_slot:        function(){return fromDom(['media_player'])||first()},
    camera_slot:       function(){return fromDom(['camera'])||''},
    primary_slot:      function(){return fromDom(['sensor','binary_sensor'])||first()},
    position_slot:     function(){return fromDom(['cover'])||first()},
    state_slot:        function(){return fromDom(['binary_sensor','sensor'])||i[1]||''},
    position_sensor_slot:function(){return fromDom(['binary_sensor','cover'])||i[1]||''},
    battery_slot:      function(){return fromDom(['sensor'])||''},
    obstruction_slot:  function(){return fromDom(['binary_sensor'])?((bd.binary_sensor||[])[1]||''):''},
    brightness_slot:   function(){return fromDom(['light'])||''},
    color_slot:        function(){return fromDom(['light'])||''},
    speed_slot:        function(){return fromDom(['fan'])||''},
    tilt_slot:         function(){return ''},
    power_slot:        function(){return fromDom(['switch','input_boolean'])||''},
    power_sensor_slot: function(){return fromDom(['sensor'])||''},
    volume_slot:       function(){return fromDom(['media_player','number','input_number'])||''},
    air_quality_slot:  function(){return fromDom(['sensor'])||''},
    filter_slot:       function(){return ''},
    humidity_sensor_slot:function(){return fromDom(['sensor'])||''},
    target_slot:       function(){return fromDom(['number','input_number'])||''},
    temperature_sensor_slot:function(){return fromDom(['sensor'])||''},
    timer_slot:        function(){return fromDom(['timer','input_number'])||''},
    motion_slot:       function(){return fromDom(['binary_sensor'])||''},
    secondary_slot:    function(){return (bd.sensor||[])[1]||''}
  };
  $('ms').querySelectorAll('select.sl').forEach(function(s){
    var k=s.getAttribute('data-s');
    var fn=hints[k];if(fn){var v=fn();if(v)s.value=v}
  });
}

/* ── WebSocket helper ── */
function wsCall(type,data){
  return getToken().then(function(token){
    return new Promise(function(ok,fail){
      var proto=location.protocol==='https:'?'wss://':'ws://';
      var ws=new WebSocket(proto+location.host+'/api/websocket');
      var mid=1;
      ws.onopen=function(){};
      ws.onerror=function(){fail(new Error('WebSocket connection failed'))};
      ws.onmessage=function(evt){
        var m=JSON.parse(evt.data);
        if(m.type==='auth_required'){ws.send(JSON.stringify({type:'auth',access_token:token}))}
        else if(m.type==='auth_ok'){var p={id:mid,type:type};Object.keys(data||{}).forEach(function(k){p[k]=data[k]});ws.send(JSON.stringify(p))}
        else if(m.type==='auth_invalid'){ws.close();fail(new Error('Auth invalid'))}
        else if(m.type==='result'){ws.close();if(m.success)ok(m.result);else fail(new Error((m.error||{}).message||'WS error'))}
      };
    });
  });
}

/* ── REST config flow fallback (walks steps one by one) ── */
function restCreate(fd){
  return haPost('/config/config_entries/flow',{handler:'homekit_architect',show_advanced_options:false})
  .then(function(step){return walkFlow(step,fd)});
}
function walkFlow(step,fd){
  if(!step||!step.flow_id)return Promise.resolve({type:'abort',reason:'No flow_id'});
  if(step.type==='create_entry'||step.type==='abort')return Promise.resolve(step);
  if(step.type!=='form')return Promise.resolve({type:'abort',reason:'Unexpected: '+step.type});
  var sid=step.step_id,fid=step.flow_id,body={};
  if(sid==='user') body={template_id:fd.template_id};
  else if(sid==='slots'){body={};var all=fd.slots||{};Object.keys(all).forEach(function(k){if(all[k])body[k]=all[k]})}
  else if(sid==='bridge') body={homekit_bridge_entry_id:fd.homekit_bridge_entry_id};
  else if(sid==='ghosting') body={automated_ghosting:fd.automated_ghosting,friendly_name:fd.friendly_name};
  else return Promise.resolve({type:'abort',reason:'Unknown step: '+sid});
  return haPost('/config/config_entries/flow/'+fid,body).then(function(next){return walkFlow(next,fd)});
}

/* ── Create accessory: try WebSocket, fall back to REST ── */
$('mk').addEventListener('click',function(){
  var btn=$('mk');btn.disabled=true;btn.textContent='Creating…';
  var atype=$('mt').value;
  var sm={};$('ms').querySelectorAll('select.sl').forEach(function(s){var k=s.getAttribute('data-s');if(k&&s.value)sm[k]=s.value});
  var name=$('mn').value||'Accessory';

  function onOk(title){btn.disabled=false;btn.textContent='Create';cm();sel={};render();toast('Created "'+esc(title)+'"','ok')}
  function onErr(e){btn.disabled=false;btn.textContent='Create';toast(String(e),'err')}

  wsCall('homekit_architect/package_accessory',{
    bridge_entry_id:bid,display_name:name,accessory_type:atype,
    entity_ids:ids(),slot_mapping:sm,hide_sources:$('mg').checked
  })
  .then(function(r){onOk(r.title||name)})
  .catch(function(wsErr){
    btn.disabled=false;btn.textContent='Create';
    showRestartBanner(String(wsErr));
  });
});

function showRestartBanner(detail){
  $('toast').innerHTML='<div class="msg err" style="line-height:1.6">'
    +'Home Assistant needs a restart to load the updated integration.<br>'
    +'<small style="color:#aaa">'+esc(detail)+'</small><br>'
    +'<button id="rbtn" class="btn bp" style="margin-top:8px">Restart Home Assistant</button>'
    +'</div>';
  $('rbtn').addEventListener('click',function(){
    $('rbtn').disabled=true;$('rbtn').textContent='Restarting…';
    haPost('/services/homeassistant/restart',{})
    .then(function(){$('toast').innerHTML='<div class="msg ok">Restarting… page will reload in 60 seconds.</div>';setTimeout(function(){location.reload()},60000)})
    .catch(function(e){$('toast').innerHTML='<div class="msg err">Could not restart: '+esc(String(e))+'</div>'});
  });
}

function toast(t,c){$('toast').innerHTML='<div class="msg '+c+'">'+t+'</div>';setTimeout(function(){$('toast').innerHTML=''},6000)}

/* ── Init ── */
(function showDebug(){
  var d=tokenData();
  var lines=[];
  lines.push('hassTokens: '+(d?'present':'MISSING'));
  if(d){
    lines.push('access_token: '+(d.access_token?d.access_token.substring(0,12)+'…':'NONE'));
    lines.push('token_expires: '+(d.token_expires?new Date(d.token_expires).toISOString():'?'));
    lines.push('expired: '+(d.token_expires?Date.now()>d.token_expires:'?'));
    lines.push('refresh_token: '+(d.refresh_token?'present':'MISSING'));
    lines.push('hassUrl: '+(d.hassUrl||'?'));
  }
  lines.push('location: '+location.origin+location.pathname);
  $('dbg').textContent=lines.join(' | ');
})();
loadBridges();
})();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[server] " + fmt % args + "\n")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())


def main():
    sys.stderr.write("[HomeKit Architect] UI server on port %d\n" % LISTEN_PORT)
    HTTPServer(("0.0.0.0", LISTEN_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
