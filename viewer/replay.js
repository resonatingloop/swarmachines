/* Pure recorded-event playback. No resimulation or inferred causal claims. */
'use strict';

const LIMITS = Object.freeze({ bytes: 5 * 1024 * 1024, events: 20000, line: 10000 });
const TYPES = new Set('run.config world.init turn.begin observation.recorded message.sent message.delivered message.seen message.acted_on action.proposed action.validated action.rejected action.committed world.changed disturbance.applied run.end policy.decision policy.report jobs.initialized job.completed'.split(' '));
const LIFECYCLE = new Set('message.sent message.delivered message.seen message.acted_on'.split(' '));
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);

function parseEpisode(text) {
  if (typeof text !== 'string' || new TextEncoder().encode(text).length > LIMITS.bytes) {
    throw new Error('episode must be text no larger than 5 mib');
  }
  const events = [];
  let runId = null;
  let previous = -1;
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    if (!line.trim()) continue;
    const fail = reason => { throw new Error(`line ${index + 1}: ${reason}`); };
    if (line.length > LIMITS.line) fail('record exceeds 10,000 characters');
    let event;
    try { event = JSON.parse(line); } catch { fail('invalid json'); }
    if (!object(event) || typeof event.run_id !== 'string' || !event.run_id ||
        !Number.isSafeInteger(event.seq) || event.seq < 0 ||
        !Number.isSafeInteger(event.turn) || event.turn < 0 ||
        !(event.agent_id === null || typeof event.agent_id === 'string') ||
        typeof event.type !== 'string' || !event.type ||
        typeof event.ts !== 'string' || !Number.isFinite(Date.parse(event.ts)) || !object(event.payload)) {
      fail('invalid event envelope');
    }
    const p = event.payload;
    if (LIFECYCLE.has(event.type)) {
      const fields = event.type === 'message.sent' ? ['message_id', 'from', 'to'] : event.type === 'message.delivered' ? ['message_id', 'to', 'status'] : ['message_id'];
      if (fields.some(key => typeof p[key] !== 'string')) fail('invalid message payload');
      if (event.type === 'message.sent' && !object(p.body)) fail('message.sent must carry an inline body object');
      if (event.type === 'message.delivered' && !['delivered', 'undelivered'].includes(p.status)) fail('invalid delivery status');
    }
    if (runId !== null && event.run_id !== runId) fail('multiple runs in one episode');
    if (event.seq <= previous) fail('event sequence must strictly increase');
    runId = event.run_id;
    previous = event.seq;
    events.push(event);
    if (events.length > LIMITS.events) fail('episode exceeds 20,000 events');
  }
  if (!events.length) throw new Error('episode contains no events');
  return { runId, events, turns: [...new Set(events.map(event => event.turn))] };
}

function snapshot(episode, cursor) {
  if (!Number.isInteger(cursor) || cursor < 0 || cursor >= episode.events.length) {
    throw new Error('cursor is outside the episode');
  }
  const messages = new Map();
  const observations = new Map();
  const disturbances = [];
  const worldChanges = [];
  let config = null;
  let initialWorld = null;
  let reportedSummary = null;
  for (let index = 0; index <= cursor; index += 1) {
    const event = episode.events[index];
    const payload = event.payload;
    if (event.type === 'run.config') config = event;
    if (event.type === 'world.init') initialWorld = event;
    if (event.type === 'world.changed') worldChanges.push(event);
    if (event.type === 'run.end') reportedSummary = event;
    if (event.type === 'disturbance.applied') disturbances.push(event);
    if (event.type === 'observation.recorded' && event.agent_id !== null) {
      observations.set(event.agent_id, event);
    }
    if (LIFECYCLE.has(event.type) && typeof payload.message_id === 'string') {
      let message = messages.get(payload.message_id);
      if (!message) {
        message = { id: payload.message_id, from: null, to: null, bodyRef: null, transitions: [] };
        messages.set(payload.message_id, message);
      }
      if (event.type === 'message.sent') {
        message.from = typeof payload.from === 'string' ? payload.from : null;
        message.to = typeof payload.to === 'string' ? payload.to : null;
        message.body = object(payload.body) ? payload.body : null;
      }
      message.transitions.push({ type: event.type, status: payload.status ?? null, event });
    }
  }
  return { event: episode.events[cursor], config, initialWorld, reportedSummary,
    messages, observations, disturbances, worldChanges };
}

const api = { LIMITS, TYPES, parseEpisode, snapshot };
if (typeof module !== 'undefined') module.exports = api;
else globalThis.Replay = api;
