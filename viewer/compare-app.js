'use strict';
const el = id => document.getElementById(id);
const slots = {left:null,right:null}, versions = {left:0,right:0};
let selectedTurn = null;
function make(tag,text,cls) { const n=document.createElement(tag); n.textContent=text; if(cls)n.className=cls; return n; }
function detail(slot,event,focus=false) {
  el(`${slot}-detail`).textContent = event ? `${slot} / ${event.run_id} / seq ${event.seq}${event.type === 'message.sent' && typeof event.payload.body !== 'string' ? ' / body unavailable; references are not fetched' : ''}\n${JSON.stringify(event,null,2)}` : `${slot} / no evidence selected`;
  if(focus) el(`${slot}-detail`).focus();
}
// Paginate every record list: preserve all evidence without unbounded DOM growth.
function recordList(slot,records,label) {
  const box=make('div','','record-list');box.append(make('p',`${slot} / ${label} (${records.length})`,'group-label'));
  const items=make('div',''),nav=make('div','');box.append(items,nav);let page=0;
  const paint=()=>{
    items.replaceChildren();nav.replaceChildren();
    for(const event of records.slice(page*40,(page+1)*40)){
      const b=make('button',`${slot} · turn ${event.turn} · seq ${event.seq} · ${event.agent_id ?? 'world'} · ${event.type}`);
      b.onclick=()=>detail(slot,event,true);items.append(b);
    }
    if(!records.length)items.append(make('p','no contributing records.','note'));
    if(records.length>40){
      const prev=make('button','previous records'),next=make('button','next records');
      prev.disabled=page===0;next.disabled=(page+1)*40>=records.length;
      prev.onclick=()=>{page--;paint();};next.onclick=()=>{page++;paint();};
      nav.append(prev,make('span',` page ${page+1} / ${Math.ceil(records.length/40)} `),next);
    }
  };paint();return box;
}
function metadata() {
  el('coverage').replaceChildren();el('config').replaceChildren();
  for(const slot of ['left','right']){
    const data=slots[slot],box=make('div','','card');
    box.append(make('h3',slot));
    box.append(make('p',data ? `${data.name} / ${data.episode.runId} / ${data.episode.events.length} records / file coverage: turns ${data.episode.turns[0]}–${data.episode.turns.at(-1)}` : 'waiting for episode'));
    if(data){box.append(make('p',data.episode.events.some(e=>e.type==='run.end') ? 'run.end recorded' : 'no run.end recorded','note'));box.append(recordList(slot,Comparison.config(data.episode),'file-level configuration records'));}
    el('coverage').append(box);
  }
  for(const row of Comparison.configuration(slots.left?.episode,slots.right?.episode)){
    const box=make('div','','config-row'),values=make('div','','config-values');
    box.append(make('p',`${row.field} / ${row.status}`));
    for(const slot of ['left','right'])values.append(make('span',`${slot}: ${row[slot]===undefined ? 'unknown / missing or conflicting' : JSON.stringify(row[slot])}`));
    box.append(values);el('config').append(box);
  }
}
function render() {
  globalThis.ExportUI?.refresh();
  const states={};el('metrics').replaceChildren();
  for(const slot of ['left','right']){
    const state=Comparison.atTurn(slots[slot]?.episode,selectedTurn);states[slot]=state;
    el(`${slot}-state`).textContent=`${slot} / ${state.status}`;
    const box=el(`${slot}-records`);box.replaceChildren();detail(slot,state.state?.event);
    if(!state.state)continue;
    const observations=[...state.state.observations.values()];
    box.append(make('p',observations.map(e=>`${e.agent_id}: observation turn ${e.turn}${e.turn<selectedTurn ? ' (carried forward)' : ''}`).join(' · ') || 'no observations in this prefix','note'));
    box.append(recordList(slot,observations,'latest observations by recorded agent id'));
    const actions=state.records.filter(e=>e.type.startsWith('action.'));
    const agents=[...new Set(actions.map(e=>e.agent_id))];
    if(!agents.length)box.append(recordList(slot,[],'action records this turn'));
    for(const agent of agents)box.append(recordList(slot,actions.filter(e=>e.agent_id===agent),`action records / agent ${agent ?? 'world'} / this turn`));
    box.append(recordList(slot,state.state.disturbances,'disturbances through this turn'));
    box.append(recordList(slot,state.records,'all records this turn'));
  }
  for(const metric of Comparison.METRICS){
    const row=make('tr','');row.append(make('th',metric));
    for(const slot of ['left','right']){
      const cell=make('td',''),records=states[slot].counts?.[metric];
      if(records){const b=make('button',String(records.length));b.setAttribute('aria-label',`${slot} ${metric}: ${records.length} records`);b.onclick=()=>{const box=el(`${slot}-records`);box.replaceChildren(recordList(slot,records,`${metric} contributors at turn ${selectedTurn}`));detail(slot,records[0],true);};cell.append(b);}else cell.textContent='—';
      row.append(cell);
    }
    row.append(make('td',states.left.available&&states.right.available ? String(states.right.counts[metric].length-states.left.counts[metric].length) : 'unavailable'));el('metrics').append(row);
  }
}
function rebuild() {
  const ts=Comparison.turns(slots.left?.episode,slots.right?.episode);selectedTurn=ts[0]??null;
  el('pair-turn').replaceChildren(...ts.map(t=>{const o=make('option',String(t));o.value=t;return o;}));el('pair-turn').disabled=!ts.length;
  metadata();render();
}
for(const slot of ['left','right'])el(`${slot}-file`).onchange=async()=>{
  const file=el(`${slot}-file`).files[0];if(!file)return;const version=++versions[slot];
  el('load-status').textContent=`loading ${slot} episode…`;
  globalThis.ExportUI?.pending(slot,true);
  try{
    if(file.size>Replay.LIMITS.bytes)throw Error('episode exceeds 5 mib');
    const bytes=await file.arrayBuffer();
    const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
    if(version!==versions[slot])return;
    const episode=Comparison.prepare(text);
    let sha256=null,hashError=null;
    try{sha256=await Evidence.sha256(bytes);}catch(error){hashError=error.message;}
    if(version!==versions[slot])return;
    slots[slot]={episode,name:file.name,sha256,byteLength:bytes.byteLength,hashError};
    globalThis.ExportUI?.sourceAccepted();
    el(`${slot}-error`).textContent='';rebuild();
  }catch(error){if(version===versions[slot])el(`${slot}-error`).textContent=`${slot}: ${error.message}. previous pair and turn retained.`;}
  finally{if(version===versions[slot]){globalThis.ExportUI?.pending(slot,false);el(`${slot}-file`).value='';el('load-status').textContent=slots.left&&slots.right ? 'two local files loaded; generation provenance unverified.' : 'waiting for second episode.';}}
};
el('pair-turn').onchange=()=>{selectedTurn=Number(el('pair-turn').value);render();};
el('reset').onclick=()=>{globalThis.ExportUI?.reset();for(const slot of ['left','right']){versions[slot]++;slots[slot]=null;el(`${slot}-file`).value='';el(`${slot}-error`).textContent='';}el('load-status').textContent='both episodes cleared.';rebuild();};
rebuild();
