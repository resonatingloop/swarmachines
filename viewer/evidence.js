/* Derived evidence only. Original logs are required to inspect source payloads. */
'use strict';
const CompareEvidence = typeof module !== 'undefined' ? require('./comparison.js') : globalThis.Comparison;
const SCHEMA = 'swarmachines.evidence-packet.v1';
const VERSION = '1.0.0';
const MAX_BYTES = 2 * 1024 * 1024;
const CAVEATS = [
  'paired files are not a certified matched experiment; equal logged settings do not establish equal worlds, policies or generation controls.',
  'counts describe records, not unique messages, successful decisions, delivered freight or causal effects.',
  'selection may omit relevant turns; selected-turn summaries are not whole-run estimates.',
  'carried-forward observations retain their recorded age; missing records and missing turns are not evidence of no activity.',
  'source hashes establish byte identity only. original source files are required for raw evidence inspection.',
  'configuration is file-level context; cursor-scoped evidence remains bounded by each selected turn.',
  'no outcome or world-backed claim is established by this export.',
  'count vocabulary covers only the comparison model’s named types; other event types remain in the source files.',
  'logged configuration and identifiers may contain producer-supplied sensitive content; this packet is not anonymized or certified safe to publish.'
];
// Iterative stable serialization: sorted object keys, original array order, JSON scalars.
function stable(value) {
  const output=[], stack=[{value}];
  while(stack.length){
    const item=stack.pop();
    if(Object.hasOwn(item,'text')){output.push(item.text);continue;}
    const v=item.value;
    if(v===null || typeof v!=='object'){const s=JSON.stringify(v);if(s===undefined)throw Error('unsupported packet value');output.push(s);continue;}
    const array=Array.isArray(v),keys=array ? v.map((_,i)=>i) : Object.keys(v).sort();
    output.push(array?'[':'{');stack.push({text:array?']':'}'});
    for(let i=keys.length-1;i>=0;i--){const k=keys[i];stack.push({value:v[k]});if(!array)stack.push({text:JSON.stringify(k)+':'});if(i>0)stack.push({text:','});}
  }
  return output.join('');
}
async function sha256(bytes) {
  if(!globalThis.crypto?.subtle)throw Error('local cryptography unavailable; export disabled');
  return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
}
function ref(slot,e){return {slot,run_id:e.run_id,seq:e.seq,turn:e.turn,type:e.type};}
function tag(configs,field){
  if(configs.length>1)return {state:'conflicting'};
  if(configs.length!==1 || !Object.hasOwn(configs[0].payload,field))return {state:'missing'};
  return {state:'present',value:configs[0].payload[field]};
}
function source(data){
  if(!data || !/^[0-9a-f]{64}$/.test(data.sha256||'') || !Number.isSafeInteger(data.byteLength))throw Error('both source byte hashes are required');
  return {sha256:data.sha256,byte_length:data.byteLength,run_id:data.episode.runId,turn_range:[data.episode.turns[0],data.episode.turns.at(-1)],event_count:data.episode.events.length,run_end_present:data.episode.events.some(e=>e.type==='run.end')};
}
function build(sources,selection){
  const selected=[...new Set(selection)].sort((a,b)=>a-b),union=CompareEvidence.turns(sources.left?.episode,sources.right?.episode);
  if(!selected.length || selected.length>32 || selected.some(t=>!Number.isSafeInteger(t)||!union.includes(t)))throw Error('select 1–32 recorded turns');
  const leftConfigs=CompareEvidence.config(sources.left?.episode),rightConfigs=CompareEvidence.config(sources.right?.episode);
  const packet={schema_version:SCHEMA,exporter_version:VERSION,scope:'selected-turn-record-comparison',sources:{left:source(sources.left),right:source(sources.right)},selection:{turns:selected,alignment:'last-record-at-or-before-turn'},configuration:{context:'file-level',fields:CompareEvidence.configuration(sources.left.episode,sources.right.episode).map(row=>({field:row.field,status:row.status,left:tag(leftConfigs,row.field),right:tag(rightConfigs,row.field)})),records:{left:leftConfigs.map(e=>ref('left',e)),right:rightConfigs.map(e=>ref('right',e))}},turns:[],observations:[],disturbances:[],limitations:[...CAVEATS]};
  for(const slot of ['left','right'])if(!packet.sources[slot].run_end_present)packet.limitations.push(`${slot}: no run.end recorded.`);
  if(stable(packet.sources.left.turn_range)!==stable(packet.sources.right.turn_range))packet.limitations.push('source turn ranges differ; horizons are unequal.');
  for(const row of packet.configuration.fields)if(row.status.includes('unknown')||row.status.includes('conflicting'))packet.limitations.push(`${row.field}: ${row.status}.`);
  for(const turn of selected){
    const states={left:CompareEvidence.atTurn(sources.left.episode,turn),right:CompareEvidence.atTurn(sources.right.episode,turn)};
    const entry={turn,left:null,right:null,delta:{}};
    for(const slot of ['left','right']){
      const state=states[slot];entry[slot]={status:state.status,counts:{},contributors:{}};
      if(!state.available)packet.limitations.push(`${slot}, turn ${turn}: ${state.status}.`);
      for(const metric of CompareEvidence.METRICS){entry[slot].counts[metric]=state.counts?.[metric].length??null;entry[slot].contributors[metric]=state.counts ? state.counts[metric].map(e=>ref(slot,e)) : null;}
      packet.observations.push({selected_turn:turn,slot,records:[...(state.state?.observations.values()||[])].map(e=>({...ref(slot,e),agent_id:e.agent_id,carried_forward:e.turn<turn}))});
      packet.disturbances.push({selected_turn:turn,slot,records:(state.state?.disturbances||[]).map(e=>ref(slot,e))});
    }
    for(const metric of CompareEvidence.METRICS)entry.delta[metric]=states.left.available&&states.right.available ? entry.right.counts[metric]-entry.left.counts[metric] : null;
    packet.turns.push(entry);
  }
  // Snapshot configuration values and freeze iteratively; never freeze caller-owned logs.
  return JSON.parse(stable(packet));
}
function text(value){
  return String(value).replace(/[\u0000-\u001f\u007f-\u009f\u2028-\u202e\u2066-\u2069]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0')).replace(/[!-/:-@\[-`{-~]/g,c=>'&#'+c.charCodeAt(0)+';');
}
function markdown(packet){
  const lines=['# selected-turn evidence packet','',`packet id: ${packet.packet_id}`,`schema: ${packet.schema_version}`,`exporter: ${packet.exporter_version}`,'',`selected turns: ${packet.selection.turns.join(', ')}`,`alignment: ${packet.selection.alignment}`,'','## sources'];
  for(const slot of ['left','right']){const s=packet.sources[slot];lines.push('',`### ${slot}`,`sha256: ${s.sha256}`,`bytes: ${s.byte_length}; records: ${s.event_count}; turns: ${s.turn_range.join('–')}; run.end present: ${s.run_end_present}`,`run id: ${text(s.run_id)}`);}
  lines.push('','## logged configuration / file-level context');
  for(const row of packet.configuration.fields)lines.push('',`- ${row.field}: ${row.status}`,`  - left: ${text(stable(row.left))}`,`  - right: ${text(stable(row.right))}`);
  for(const slot of ['left','right'])lines.push(`- ${slot} configuration references: ${text(stable(packet.configuration.records[slot]))}`);
  for(const turn of packet.turns){
    lines.push('',`## turn ${turn.turn}`,`left: ${turn.left.status}; right: ${turn.right.status}`,'','| event count | left | right | right − left |','|---|---:|---:|---:|');
    for(const metric of CompareEvidence.METRICS)lines.push(`| ${metric} | ${turn.left.counts[metric]??'unavailable'} | ${turn.right.counts[metric]??'unavailable'} | ${turn.delta[metric]??'unavailable'} |`);
    lines.push('','supporting references:');
    for(const slot of ['left','right'])for(const metric of CompareEvidence.METRICS)lines.push(`- ${slot} ${metric}: ${turn[slot].contributors[metric]===null ? 'unavailable' : text(stable(turn[slot].contributors[metric]))}`);
    for(const kind of ['observations','disturbances'])for(const item of packet[kind].filter(x=>x.selected_turn===turn.turn))lines.push(`- ${item.slot} ${kind}: ${text(stable(item.records))}`);
  }
  lines.push('','## limitations',...packet.limitations.map(s=>'- '+text(s)),'');return lines.join('\n');
}
async function prepare(sources,selection){
  const packet=build(sources,selection),encoded=new TextEncoder();
  const base=stable(packet);
  if(encoded.encode(base).length>MAX_BYTES)throw Error('select fewer turns: evidence exceeds 2 mib');
  packet.packet_id=await sha256(encoded.encode(base));
  const json=stable(packet)+'\n',md=markdown(packet);
  const sizes={json:encoded.encode(json).length,markdown:encoded.encode(md).length};
  if(sizes.json>MAX_BYTES||sizes.markdown>MAX_BYTES)throw Error('select fewer turns: evidence exceeds 2 mib');
  const stack=[packet];while(stack.length){const o=stack.pop();Object.freeze(o);for(const v of Object.values(o))if(v&&typeof v==='object')stack.push(v);}
  return Object.freeze({packet,json,markdown:md,sizes:Object.freeze(sizes)});
}
const Evidence={SCHEMA,VERSION,MAX_BYTES,CAVEATS,stable,sha256,build,markdown,prepare};
if(typeof module!=='undefined')module.exports=Evidence;else globalThis.Evidence=Evidence;
