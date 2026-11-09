'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {prepare,turns,atTurn,configuration}=require('./comparison.js');
const event=(seq,turn,type='turn.begin',payload={})=>({run_id:'same',seq,turn,type,payload,agent_id:'a',ts:'2026-11-07T00:00:00Z'});
const parse=events=>prepare(events.map(e=>JSON.stringify(e)).join('\n'));
test('turn end aligns unequal sequences and excludes future evidence',()=>{
 const left=parse([event(0,0),event(1,1,'observation.recorded',{v:1}),event(2,1),event(3,3,'run.end')]);
 const right=parse([event(0,1),event(1,2)]);
 assert.deepEqual(turns(left,right),[0,1,2,3]);
 assert.equal(atTurn(left,1).cursor,2);assert.equal(atTurn(right,1).cursor,0);
 assert.equal(atTurn(right,0).state,null);
 assert.equal(atTurn(left,2).counts,null);assert.equal(atTurn(left,2).state.observations.get('a').turn,1);
 assert.equal(atTurn(right,3).status,'beyond recorded horizon');
 assert.equal(atTurn(left,1).state.reportedSummary,null);
});
test('same identifiers stay independent and counts retain exact contributors',()=>{
 const sent=event(0,1,'message.sent',{message_id:'m',from:'a',to:'b',body:{type:'report',content:'status from a'}});
 const left=parse([sent,event(1,1,'message.delivered',{message_id:'m',to:'b',status:'delivered'})]);
 const right=parse([sent,event(1,1,'message.delivered',{message_id:'m',to:'b',status:'undelivered'})]);
 assert.equal(atTurn(left,1).counts.delivered.length,1);assert.equal(atTurn(right,1).counts.delivered.length,0);
 assert.equal(atTurn(right,1).counts.undelivered[0],right.events[1]);
 assert.notEqual(atTurn(left,1).state.messages.get('m'),atTurn(right,1).state.messages.get('m'));
 assert.equal(atTurn(null,1).counts,null);
});
test('configuration distinguishes missing, null, structural equality and conflicts',()=>{
 const a=parse([event(0,0,'run.config',{seed:null,agents:['a','b'],disturbance_schedule:{x:1,y:2}})]);
 const b=parse([event(0,0,'run.config',{seed:null,agents:['b','a'],disturbance_schedule:{y:2,x:1}})]);
 const rows=configuration(a,b);
 assert.equal(rows[0].status,'equal logged values');assert.equal(rows[1].status,'different logged values');
 assert.equal(rows[2].status,'unknown / missing');assert.equal(rows[3].status,'equal logged values');
 assert.equal(configuration(a,parse([event(0,0,'run.config')]))[0].status,'unknown / missing');
 assert.ok(configuration(parse([event(0,0,'run.config'),event(1,1,'run.config')]),b).every(r=>r.status==='conflicting config records'));
});
test('comparison rejects descending turns without changing single-episode parser',()=>{
 const text=[event(0,2),event(1,1)].map(JSON.stringify).join('\n');
 assert.throws(()=>prepare(text),/nondecreasing turns/);
 assert.equal(require('./replay.js').parseEpisode(text).events.length,2);
});
test('representative upper limit keeps exact evidence',()=>{
 const rows=Array.from({length:20000},(_,i)=>event(i,Math.floor(i/200),'action.committed',{action_id:'a'}));
 const e=parse(rows);assert.equal(atTurn(e,50).counts['action.committed'].length,200);
 assert.equal(atTurn(e,99).cursor,19999);
});
