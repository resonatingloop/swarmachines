'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { parseEpisode, snapshot } = require('./replay.cjs');
const text = fs.readFileSync(path.join(__dirname, '../runtime/sample-run.jsonl'), 'utf8');
const episode = parseEpisode(text);

test('reads the merged runner artifact with its original identities', () => {
  assert.equal(episode.events.length, 67);
  assert.equal(episode.runId, 'run-seed0007');
  assert.deepEqual(episode.turns, [0, 1, 2, 3]);
});

test('rewinding never leaks future messages, disturbances or run summaries', () => {
  const last = snapshot(episode, episode.events.length - 1);
  assert.equal(last.messages.size, 8);
  assert.ok(last.reportedSummary);
  const first = snapshot(episode, 0);
  assert.equal(first.messages.size, 0);
  assert.equal(first.disturbances.length, 0);
  assert.equal(first.reportedSummary, null);
  assert.equal(first.initialWorld, null);
});

test('undelivered transitions stay distinct from delivered and seen', () => {
  const state = snapshot(episode, 66);
  const failed = [...state.messages.values()].filter(message =>
    message.transitions.some(transition => transition.status === 'undelivered'));
  assert.equal(failed.length, 2);
  for (const message of failed) {
    assert.equal(message.transitions.some(transition => transition.type === 'message.seen'), false);
  }
});

test('playback uses sequence order even when recorded timestamps go backward', () => {
  assert.ok(episode.events.some((event, index) => index && event.ts < episode.events[index - 1].ts));
  assert.equal(snapshot(episode, 8).event.seq, 8);
});

test('rejects malformed, mixed-run and duplicate records with line evidence', () => {
  assert.throws(() => parseEpisode('{}'), /line 1/);
  assert.throws(() => parseEpisode(''), /no events/);
  const first = JSON.stringify(episode.events[0]);
  assert.throws(() => parseEpisode(first+'\n'+first), /line 2.*strictly increase/);
  assert.throws(() => parseEpisode(first+'\n'+JSON.stringify({ ...episode.events[1], run_id: 'other' })), /multiple runs/);
});

test('free-form world updates and reported summaries remain source records', () => {
  const state = snapshot(episode, 66);
  assert.equal(state.worldChanges[0], episode.events[2]);
  assert.equal(state.reportedSummary, episode.events[66]);
  assert.deepEqual(state.initialWorld.payload.routes, episode.events[1].payload.routes);
  assert.throws(() => snapshot(episode, 67), /outside/);
});

test('bounds input and retains unknown records without deriving message state', () => {
  assert.throws(() => parseEpisode(' '.repeat(5*1024*1024+1)), /5 mib/);
  assert.throws(() => parseEpisode(' '.repeat(10001)+'{}'), /10,000/);
  const unknown = {...episode.events[0], type:'message.future', payload:{message_id:'x', extra:'<img src=x onerror=alert(1)>'}};
  const parsed = parseEpisode(JSON.stringify(unknown));
  assert.deepEqual(parsed.events[0], unknown);
  assert.equal(snapshot(parsed, 0).messages.size, 0);
});

test('lifecycle payload validation and safe sequence gaps', () => {
  const event = episode.events.find(e => e.type === 'message.sent');
  assert.throws(() => parseEpisode(JSON.stringify({...event, payload:{message_id:'x'}})), /message payload/);
  const first = episode.events[0];
  const parsed = parseEpisode(JSON.stringify(first)+'\n'+JSON.stringify({...episode.events[1],seq:99}));
  assert.equal(parsed.events[1].seq,99);
  assert.throws(() => parseEpisode(JSON.stringify({...first,ts:'not a date'})), /envelope/);
});

test('record count ceiling and exact bundled sample provenance', () => {
  const vm = require('node:vm');
  const context = {};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'sample.js'), 'utf8'), context);
  assert.equal(context.SAMPLE_EPISODE, text);
  // minimal records keep the count fixture below the separate byte ceiling.
  const small = Array.from({length:20001}, (_,seq) => JSON.stringify({run_id:'r',seq,turn:0,agent_id:null,type:'x',ts:'2026-01-01T00:00:00Z',payload:{}})).join('\n');
  assert.throws(() => parseEpisode(small), /20,000 events/);
});

test('pinned freight candidate is reproducible compatibility data, not world-backed evidence', () => {
  const crypto = require('node:crypto');
  const raw = fs.readFileSync(path.join(__dirname, 'fixtures/freight-candidate.jsonl'));
  const provenance = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/freight-candidate.provenance.json')));
  assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), provenance.sha256);
  assert.equal(provenance.world_backed, false);
  const freight = parseEpisode(raw.toString('utf8'));
  assert.equal(freight.events.length, provenance.records);
  assert.deepEqual(freight.turns, Array.from({length:17}, (_,i)=>i));
  for (let cursor = 0; cursor < freight.events.length; cursor++) {
    const state = snapshot(freight, cursor);
    const prefix = freight.events.slice(0, cursor + 1);
    assert.equal(state.event, freight.events[cursor]);
    assert.equal(state.reportedSummary, prefix.find(e=>e.type==='run.end') ?? null);
    assert.deepEqual(state.disturbances, prefix.filter(e=>e.type==='disturbance.applied'));
    for (const [agent, observation] of state.observations) {
      assert.equal(observation, prefix.filter(e=>e.agent_id===agent && e.type==='observation.recorded').at(-1));
    }
    for (const message of state.messages.values()) {
      assert.deepEqual(message.transitions.map(t=>t.event), prefix.filter(e=>e.type.startsWith('message.') && e.payload.message_id===message.id));
    }
  }
  const state = snapshot(freight,393);
  assert.equal(state.messages.size,71);
  assert.equal([...state.messages.values()].filter(m=>m.transitions.some(t=>t.status==='undelivered')).length,20);
  assert.equal(snapshot(freight,0).messages.size,0);
});

 test('policy records remain recorded evidence without fabricated influence', () => {
  const { TYPES } = require('./replay.cjs');
  const records = ['policy.report', 'policy.decision'].map((type, seq) => ({
    run_id: 'fixture', seq, turn: 1, agent_id: 'a', type,
    ts: '2026-11-07T14:30:00Z', payload: { reason: 'fixture only' }
  }));
  const parsed = parseEpisode(records.map(JSON.stringify).join('\n'));
  for (const record of parsed.events) assert.ok(TYPES.has(record.type));
  assert.equal(snapshot(parsed, 1).messages.size, 0);
  assert.deepEqual(parsed.events, records);
});
