/* Logical-turn comparison. Record counts do not measure causal effects. */
'use strict';
const ReplayModel = typeof module !== 'undefined' ? require('./replay.js') : globalThis.Replay;
const METRICS = ['sent', 'delivered', 'undelivered', 'seen', 'acted_on', 'action.proposed', 'action.validated', 'action.committed', 'action.rejected'];
const CONFIG_FIELDS = ['seed', 'agents', 'comm_topology', 'disturbance_schedule', 'delivery_config_sha'];
function prepare(text) {
  const episode = ReplayModel.parseEpisode(text);
  for (let i = 1; i < episode.events.length; i++) {
    if (episode.events[i].turn < episode.events[i - 1].turn) {
      throw new Error(`comparison requires nondecreasing turns; seq ${episode.events[i].seq}`);
    }
  }
  return episode;
}
function turns(left, right) {
  return [...new Set([...(left?.turns || []), ...(right?.turns || [])])].sort((a,b)=>a-b);
}
function atTurn(episode, turn) {
  if (!episode) return { status: 'waiting for episode', available: false, records: [], state: null, counts: null };
  const records = episode.events.filter(e=>e.turn === turn);
  let cursor = -1;
  for (let i = 0; i < episode.events.length && episode.events[i].turn <= turn; i++) cursor = i;
  const available = records.length > 0;
  const counts = Object.fromEntries(METRICS.map(key=>[key, []]));
  for (const e of records) {
    let key = e.type.startsWith('message.') ? e.type.slice(8) : e.type;
    if (e.type === 'message.delivered') key = e.payload.status;
    if (Object.hasOwn(counts,key)) counts[key].push(e);
  }
  return { available, records, cursor,
    status: available ? 'records at this turn' : turn > episode.turns.at(-1) ? 'beyond recorded horizon' : 'no records for this turn',
    state: cursor < 0 ? null : ReplayModel.snapshot(episode,cursor), counts: available ? counts : null };
}
function equalJSON(left, right) {
  const pending = [[left,right]];
  while (pending.length) {
    const [a,b] = pending.pop();
    if (a === b) continue;
    if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object' || Array.isArray(a)!==Array.isArray(b)) return false;
    const keys=Object.keys(a);
    if(keys.length!==Object.keys(b).length) return false;
    for(const key of keys) {
      if(!Object.hasOwn(b,key)) return false;
      pending.push([a[key],b[key]]);
    }
  }
  return true;
}
function config(episode) { return episode?.events.filter(e=>e.type==='run.config') || []; }
function configuration(left, right) {
  const a = config(left), b = config(right);
  return CONFIG_FIELDS.map(field=>{
    const present = list => list.length===1 && Object.hasOwn(list[0].payload,field);
    const l = present(a), r = present(b);
    return { field, left: l ? a[0].payload[field] : undefined, right: r ? b[0].payload[field] : undefined,
      status: a.length>1 || b.length>1 ? 'conflicting config records' : !l || !r ? 'unknown / missing' : equalJSON(a[0].payload[field],b[0].payload[field]) ? 'equal logged values' : 'different logged values' };
  });
}
const Comparison = { prepare, turns, atTurn, configuration, config, METRICS };
if (typeof module !== 'undefined') module.exports = Comparison;
else globalThis.Comparison = Comparison;
