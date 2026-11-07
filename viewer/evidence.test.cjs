'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const E=require('./evidence.js'),C=require('./comparison.js');
const event=(seq,turn,type,payload={})=>({run_id:'same|<script>\n',seq,turn,type,payload,agent_id:'a',ts:'2026-11-07T00:00:00Z'});
async function source(events,newline='\n'){
 const bytes=Buffer.from(events.map(JSON.stringify).join(newline));return {episode:C.prepare(bytes.toString()),sha256:await E.sha256(bytes),byteLength:bytes.length,name:'/private/never-export.jsonl'};
}
const rows=[event(0,0,'run.config',{seed:null,agents:['a'],comm_topology:'<b>mesh</b>'}),event(1,1,'observation.recorded',{secret:'PRIVATE OBSERVATION'}),event(2,1,'message.sent',{message_id:'m',from:'a',to:'b',body_ref:'private.txt',body:'PRIVATE MESSAGE'}),event(3,3,'run.end',{deliveries_completed:12345})];
test('deterministic packet identity independently recomputes and excludes raw fields',async()=>{
 const sources={left:await source(rows),right:await source(rows)};
 const a=await E.prepare(sources,[3,1,1]),b=await E.prepare(sources,[1,3]);assert.equal(a.json,b.json);
 const {packet_id,...base}=JSON.parse(a.json);
 const independent=value=>Array.isArray(value)?value.map(independent):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,independent(value[k])])):value;
 assert.equal(packet_id,crypto.createHash('sha256').update(JSON.stringify(independent(base))).digest('hex'));
 for(const value of ['PRIVATE MESSAGE','PRIVATE OBSERVATION','private.txt','never-export','deliveries_completed']){assert.ok(!a.json.includes(value));assert.ok(!a.markdown.includes(value));}
 assert.ok(a.markdown.includes(packet_id));assert.ok(Object.isFrozen(a.packet.sources));
 assert.equal(a.packet.turns[0].left.counts.sent,1);assert.equal(a.packet.turns[0].left.contributors.sent[0].slot,'left');
 assert.equal(a.packet.turns[0].right.contributors.sent[0].slot,'right');
});
test('byte provenance preserves line endings, unavailable and null config differ from missing',async()=>{
 const left=await source(rows),right=await source([rows[0],event(1,2,'turn.begin')],'\r\n');
 const lf=await source(rows),crlf=await source(rows,'\r\n');assert.notEqual(lf.sha256,crlf.sha256);assert.deepEqual(lf.episode,crlf.episode);
 const p=(await E.prepare({left,right},[1,2,3])).packet;
 assert.equal(p.turns[0].right.counts.sent,null);assert.equal(p.turns[0].delta.sent,null);
 assert.equal(p.turns[1].right.counts.sent,0);assert.equal(p.turns[1].left.counts.sent,null);
 assert.equal(p.configuration.fields[0].left.state,'present');assert.equal(p.configuration.fields[0].left.value,null);
 assert.equal(p.configuration.fields.find(f=>f.field==='delivery_config_sha').left.state,'missing');
 assert.equal(p.observations.find(o=>o.slot==='left'&&o.selected_turn===3).records[0].carried_forward,true);
 assert.ok(!E.markdown({...p,packet_id:'x'}).includes('<script>'));
});
test('selection and output bounds refuse rather than truncate',async()=>{
 const data=await source(rows);assert.throws(()=>E.build({left:data,right:data},[]),/1–32/);assert.throws(()=>E.build({left:data,right:data},[99]),/1–32/);
 const huge=await source(Array.from({length:14000},(_,i)=>event(i,1,'message.seen',{message_id:'m'})));
 await assert.rejects(()=>E.prepare({left:huge,right:huge},[1]),/select fewer turns/);
});
test('conflicting config preserved and future evidence excluded',async()=>{
 const data=await source([...rows.slice(0,3),event(3,2,'disturbance.applied',{kind:'secret',detail:{body:'PRIVATE'}}),event(4,3,'run.config',{})]);
 const p=(await E.prepare({left:data,right:data},[1])).packet;
 assert.ok(p.configuration.fields.every(f=>f.status==='conflicting config records'));
 assert.equal(p.configuration.records.left.length,2);assert.equal(p.disturbances[0].records.length,0);
 assert.ok(p.turns[0].left.contributors.sent.every(r=>r.turn<=1));
});
