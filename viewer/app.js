'use strict';
const $ = id => document.getElementById(id);
let episode = null, cursor = 0, timer = null, loadVersion = 0;
const node = (tag, text, className) => {
  const el = document.createElement(tag); el.textContent = text;
  if (className) el.className = className;
  return el;
};
function pause() { clearInterval(timer); timer = null; $('play').textContent = 'play'; }
function inspect(event) {
  $('detail-title').textContent = `${event.run_id} / seq ${event.seq} / turn ${event.turn} / ${event.type}${Replay.TYPES.has(event.type) ? '' : ' / unsupported type'}`;
  $('detail').textContent = JSON.stringify(event, null, 2);
}
function recordButton(event, label) {
  const b = node('button', label || `seq ${event.seq} · ${event.type}`);
  b.onclick = () => { pause(); inspect(event); $('detail').focus(); }; return b;
}
function render() {
  const state = Replay.snapshot(episode, cursor);
  $('position').textContent = `${cursor + 1} / ${episode.events.length} records`;
  $('cursor').value = cursor; $('turn').value = state.event.turn;
  $('current').textContent = `seq ${state.event.seq} / turn ${state.event.turn} / ${state.event.type}`;
  $('prev').disabled = cursor === 0; $('next').disabled = cursor === episode.events.length - 1;
  $('play').disabled = cursor === episode.events.length - 1;
  const gaps = episode.events.slice(0, cursor + 1).filter((e, i) => i && e.seq !== episode.events[i-1].seq + 1).length;
  $('warnings').textContent = `${gaps ? `${gaps} sequence gap(s) in the visible record. ` : ''}${Replay.TYPES.has(state.event.type) ? '' : 'unsupported event type; raw record retained.'}`;
  inspect(state.event);
  $('agents').replaceChildren();
  for (const [agent, event] of state.observations) {
    const card = node('div', '', 'card'); card.append(node('p', agent), recordButton(event)); $('agents').append(card);
  }
  if (!state.observations.size) $('agents').append(node('p', 'no observations recorded yet.', 'note'));
  $('messages').replaceChildren();
  for (const message of state.messages.values()) {
    const card = node('div', '', 'card');
    card.append(node('p', `${message.id} / ${message.from ?? 'unknown sender'} → ${message.to ?? 'unknown recipient'}`));
    const sent = message.transitions.find(t => t.type === 'message.sent');
    const body = sent?.event.payload.body;
    const bodyText = body && typeof body === 'object'
      ? (typeof body.content === 'string' ? body.content : JSON.stringify(body))
      : 'body unavailable';
    card.append(node('p', bodyText, 'note'));
    let delivered = false, seen = false, hasSent = false;
    const warnings = [];
    for (const t of message.transitions) {
      if (t.type === 'message.sent') { if (hasSent) warnings.push('repeated sent record'); hasSent = true; }
      else if (!hasSent) warnings.push('transition without preceding sent record');
      if (t.type === 'message.delivered') {
        delivered = t.status === 'delivered';
        if (!delivered && typeof t.event.payload.reason !== 'string') warnings.push('undelivered reason absent');
      }
      if (t.type === 'message.seen') { if (!delivered) warnings.push('seen without preceding delivery'); seen = true; }
      if (t.type === 'message.acted_on' && !seen) warnings.push('acted on without preceding seen record');
      card.append(recordButton(t.event, `#${t.event.seq} ${t.status ?? t.type.slice(8)}${t.event.payload.reason ? ` / ${t.event.payload.reason}` : ''}`));
    }
    if (warnings.length) card.append(node('p', [...new Set(warnings)].join('; '), 'warning'));
    $('messages').append(card);
  }
  if (!state.messages.size) $('messages').append(node('p', 'no message records yet.', 'note'));
  $('world').replaceChildren();
  for (const [event, label] of [[state.config,'run configuration'],[state.initialWorld,'as recorded at initialization'],...state.worldChanges.map(e=>[e,'world change record']),...state.disturbances.map(e=>[e,'disturbance record']),[state.reportedSummary,'reported summary']]) {
    if (event) $('world').append(recordButton(event, `${label} / seq ${event.seq}`));
  }
}
function go(index) { pause(); cursor = index; render(); }
function install(text, source) {
  const parsed = Replay.parseEpisode(text); episode = parsed; cursor = 0;
  $('identity').textContent = `${episode.runId} / ${episode.events.length} records`;
  $('source').textContent = source;
  $('error').textContent = '';
  $('turn').replaceChildren(...episode.turns.map(turn => { const o = node('option', String(turn)); o.value = turn; return o; }));
  $('turn').disabled = false; $('cursor').disabled = false; $('cursor').max = episode.events.length - 1;
  render();
}
$('sample').onclick = () => {
  loadVersion++; pause(); install(SAMPLE_EPISODE, 'bundled scripted runner sample / seed 7 · 3 turns · relay-loss. observations, acted-on flags and summary values are scaffolding, not measured freight outcomes.');
};
$('file').onchange = async () => {
  const version = ++loadVersion; pause(); const file = $('file').files[0];
  if (!file) return;
  try {
    if (file.size > Replay.LIMITS.bytes) throw new Error('episode exceeds 5 mib');
    const text = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer());
    if (version !== loadVersion) return;
    install(text, `local file: ${file.name} / provenance supplied by the file; viewer has not verified how it was produced. nothing uploaded or saved.`);
  } catch (error) { if (version === loadVersion) $('error').textContent = `could not load episode: ${error.message}. previous episode retained, paused.`; }
  finally { if (version === loadVersion) $('file').value = ''; }
};
$('prev').onclick = () => go(cursor - 1);
$('next').onclick = () => go(cursor + 1);
$('cursor').oninput = () => go(Number($('cursor').value));
$('turn').onchange = () => go(episode.events.findIndex(e => e.turn === Number($('turn').value)));
$('play').onclick = () => {
  if (timer) return pause();
  $('play').textContent = 'pause';
  timer = setInterval(() => { cursor++; render(); if (cursor === episode.events.length - 1) pause(); }, 650);
};
