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
  "count vocabulary covers only the comparison model's named types; other event types remain in the source files.",
  'logged configuration and identifiers may contain producer-supplied sensitive content; this packet is not anonymized or certified safe to publish.'
];

/**
 * Map of bidi/control characters to their escaped representations.
 * These characters can visually reorder text in markdown renderers,
 * enabling attacks that hide or misrepresent content.
 * Includes: C0/C1 controls, U+2028/2029, bidi overrides/isolates/marks, ZWJ/ZWNJ/SHY/BOM.
 * @type {Map<string, string>}
 */
const BIDI_ESCAPE_MAP = new Map([
  // C0 controls (0x00-0x1F) except \t, \n, \r which are handled separately
  ['\u0000', '\\u0000'], ['\u0001', '\\u0001'], ['\u0002', '\\u0002'], ['\u0003', '\\u0003'],
  ['\u0004', '\\u0004'], ['\u0005', '\\u0005'], ['\u0006', '\\u0006'], ['\u0007', '\\u0007'],
  ['\u0008', '\\u0008'], ['\u0009', '\\u0009'], // tab
  ['\u000B', '\\u000B'], ['\u000C', '\\u000C'],
  ['\u000E', '\\u000E'], ['\u000F', '\\u000F'], ['\u0010', '\\u0010'], ['\u0011', '\\u0011'],
  ['\u0012', '\\u0012'], ['\u0013', '\\u0013'], ['\u0014', '\\u0014'], ['\u0015', '\\u0015'],
  ['\u0016', '\\u0016'], ['\u0017', '\\u0017'], ['\u0018', '\\u0018'], ['\u0019', '\\u0019'],
  ['\u001A', '\\u001A'], ['\u001B', '\\u001B'], ['\u001C', '\\u001C'], ['\u001D', '\\u001D'],
  ['\u001E', '\\u001E'], ['\u001F', '\\u001F'],
  // DEL and C1 controls (0x7F-0x9F)
  ['\u007F', '\\u007F'], ['\u0080', '\\u0080'], ['\u0081', '\\u0081'], ['\u0082', '\\u0082'],
  ['\u0083', '\\u0083'], ['\u0084', '\\u0084'], ['\u0085', '\\u0085'], ['\u0086', '\\u0086'],
  ['\u0087', '\\u0087'], ['\u0088', '\\u0088'], ['\u0089', '\\u0089'], ['\u008A', '\\u008A'],
  ['\u008B', '\\u008B'], ['\u008C', '\\u008C'], ['\u008D', '\\u008D'], ['\u008E', '\\u008E'],
  ['\u008F', '\\u008F'], ['\u0090', '\\u0090'], ['\u0091', '\\u0091'], ['\u0092', '\\u0092'],
  ['\u0093', '\\u0093'], ['\u0094', '\\u0094'], ['\u0095', '\\u0095'], ['\u0096', '\\u0096'],
  ['\u0097', '\\u0097'], ['\u0098', '\\u0098'], ['\u0099', '\\u0099'], ['\u009A', '\\u009A'],
  ['\u009B', '\\u009B'], ['\u009C', '\\u009C'], ['\u009D', '\\u009D'], ['\u009E', '\\u009E'],
  ['\u009F', '\\u009F'],
  // Line/paragraph separators
  ['\u2028', '\\u2028'], // LS (Line Separator)
  ['\u2029', '\\u2029'], // PS (Paragraph Separator)
  // Bidi formatting controls
  ['\u200E', '\\u200E'], // LRM (Left-to-Right Mark)
  ['\u200F', '\\u200F'], // RLM (Right-to-Left Mark)
  ['\u061C', '\\u061C'], // ALM (Arabic Letter Mark)
  ['\u202A', '\\u202A'], // LRE (Left-to-Right Embedding)
  ['\u202B', '\\u202B'], // RLE (Right-to-Left Embedding)
  ['\u202C', '\\u202C'], // PDF (Pop Directional Formatting)
  ['\u202D', '\\u202D'], // LRO (Left-to-Right Override)
  ['\u202E', '\\u202E'], // RLO (Right-to-Left Override)
  ['\u2066', '\\u2066'], // LRI (Left-to-Right Isolate)
  ['\u2067', '\\u2067'], // RLI (Right-to-Left Isolate)
  ['\u2068', '\\u2068'], // FSI (First Strong Isolate)
  ['\u2069', '\\u2069'], // PDI (Pop Directional Isolate)
  // Zero-width and special format chars (optional coverage)
  ['\u200B', '\\u200B'], // ZWSP (Zero Width Space)
  ['\u200C', '\\u200C'], // ZWNJ (Zero Width Non-Joiner)
  ['\u200D', '\\u200D'], // ZWJ (Zero Width Joiner)
  ['\u00AD', '\\u00AD'], // SHY (Soft Hyphen)
  ['\uFEFF', '\\uFEFF'], // BOM/ZWNBSP (Byte Order Mark)
]);

// Regex pattern for bidi/control characters (for testing presence)
const BIDI_CHAR_TEST_PATTERN = new RegExp(
  `[${Array.from(BIDI_ESCAPE_MAP.keys()).join('')}]`
);

/**
 * Escape bidi and control characters in a string to prevent visual
 * reordering attacks in exported markdown.
 *
 * Each matched character is replaced with its \\uXXXX escape sequence,
 * making the character visible and neutral in the rendered output.
 *
 * @param {string} text - The input text to escape.
 * @returns {string} The text with bidi/control characters escaped.
 *
 * @example
 * escapeBidi('Hello\u200F World') // returns 'Hello\\u200F World'
 * @example
 * escapeBidi('Normal text') // returns 'Normal text' (unchanged)
 */
function escapeBidi(text) {
  if (typeof text !== 'string') {
    return String(text);
  }
  let result = text;
  for (const [char, escape] of BIDI_ESCAPE_MAP) {
    result = result.split(char).join(escape);
  }
  return result;
}

/**
 * Escape markdown-special characters that could break formatting or
 * enable injection attacks. This handles standard markdown metacharacters
 * that are dangerous in inline text context.
 *
 * For general inline text, escapes: backslash, backtick, asterisk, underscore,
 * curly braces, square brackets, parentheses, hash.
 * For table cells, only escapes: pipe, backtick.
 *
 * Note: Dots, dashes, plus, minus are NOT escaped as they are safe in
 * both inline and table contexts. List markers (+, -, *) at line start
 * are a formatting concern but not a security issue for escaped content.
 *
 * @param {string} text - The input text to escape.
 * @param {Object} [options] - Escaping options.
 * @param {boolean} [options.forTableCell=false] - If true, use table-cell-safe escaping.
 * @returns {string} The text with markdown metacharacters escaped.
 *
 * @example
 * escapeMarkdown('Hello *world*') // returns 'Hello \\*world\\*'
 */
function escapeMarkdown(text, options = {}) {
  const { forTableCell = false } = options;
  if (typeof text !== 'string') {
    return String(text);
  }
  // Escape backslashes first to avoid double-escaping
  let result = text.replace(/\\/g, '\\\\');
  
  if (forTableCell) {
    // For table cells, only escape pipe (breaks columns) and backtick (code)
    result = result.replace(/([`|])/g, '\\$1');
  } else {
    // For inline text, escape chars that could break formatting
    // Backtick (code), asterisk/underscore (emphasis), brackets (links),
    // parens (links/images), braces (mustache), hash (headings)
    result = result.replace(/([`*_{}[\]()#])/g, '\\$1');
  }
  return result;
}

/**
 * Combined escape function for markdown export: applies both
 * bidi/control character escaping and markdown metacharacter escaping.
 *
 * Order: bidi escaping first, then markdown escaping.
 *
 * @param {string} text - The input text to escape.
 * @param {Object} [options] - Escaping options passed to escapeMarkdown.
 * @returns {string} The fully escaped text safe for markdown export.
 *
 * @example
 * escapeForMarkdown('Hello\u200F *world*')
 * // returns '\\\\u200F \\*world\\*'
 */
function escapeForMarkdown(text, options) {
  const bidiEscaped = escapeBidi(text);
  return escapeMarkdown(bidiEscaped, options);
}

/**
 * Check if a string contains any bidi/control characters.
 *
 * @param {string} text - The input text to check.
 * @returns {boolean} True if bidi/control characters are present.
 */
function containsBidiChars(text) {
  if (typeof text !== 'string') {
    return false;
  }
  return BIDI_CHAR_TEST_PATTERN.test(text);
}

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

/**
 * Escape text for safe markdown export.
 * - Escapes C0/C1 controls (except \t, \n, \r which get special handling)
 * - Escapes U+2028/2029 (line/paragraph separators)
 * - Escapes all bidi formatting chars (LRM/RLM/ALM, LRE/RLE/LRO/RLO, LRI/RLI/FSI/PDI)
 * - Escapes optional format chars (ZWSP/ZWNJ/ZWJ/SHY/BOM)
 * - Escapes & FIRST to prevent numeric entity injection (e.g., &#x202E;)
 * - Escapes < and > with numeric entities to prevent HTML/script injection
 * - Escapes \n and \r to prevent markdown breakout via forged headings/links
 * - Escapes punctuation with numeric entities (original master behavior)
 *
 * @param {string} value - The value to escape.
 * @returns {string} The escaped text safe for markdown.
 */
function text(value) {
  let str = String(value);
  // First escape & to prevent numeric entity injection like &#x202E;
  str = str.replace(/&/g, '&amp;');
  // Escape < and > to prevent HTML/script injection
  str = str.replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // Escape newlines and carriage returns to prevent markdown breakout
  str = str.replace(/\n/g, '\\n').replace(/\r/g, '\\r');
  // Escape bidi/control characters using the map
  str = escapeBidi(str);
  // Escape punctuation with numeric entities (original master behavior for safety)
  // This covers: !-/:-@[-`{-~ range which includes many markdown-sensitive chars
  str = str.replace(/[!-/:-@[\]-`{-~]/g, c => '&#' + c.charCodeAt(0) + ';');
  return str;
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

// Export both the legacy API and new helper functions
const Evidence = {
  SCHEMA, VERSION, MAX_BYTES, CAVEATS,
  stable, sha256, build, markdown, prepare, text,
  // New helper exports for testing and direct use
  escapeBidi, escapeMarkdown, escapeForMarkdown, containsBidiChars,
  // Export BIDI_ESCAPE_MAP for inspection/testing
  BIDI_ESCAPE_MAP,
};

if (typeof module !== 'undefined') {
  module.exports = Evidence;
} else {
  globalThis.Evidence = Evidence;
}

// ESM named export shim for node --test compatibility
// This allows the ESM test file to import named exports from this CJS module
if (typeof globalThis.ESM_EXPORTS === 'undefined') {
  globalThis.ESM_EXPORTS = {};
}
globalThis.ESM_EXPORTS['./evidence.js'] = Evidence;
