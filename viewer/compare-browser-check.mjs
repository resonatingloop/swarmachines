import fs from 'node:fs/promises';
import {spawn} from 'node:child_process';
const profile=await fs.mkdtemp('/tmp/swarm-replay-browser-');
const chrome=spawn(process.env.CHROME_BIN || '/usr/bin/google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--no-first-run','--disable-background-networking','--disable-default-apps','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
let ws;
try {
 let port;
 for(let i=0;i<50;i++){try{port=(await fs.readFile(profile+'/DevToolsActivePort','utf8')).split('\n')[0];break;}catch{await new Promise(r=>setTimeout(r,100));}}
 if(!port)throw new Error('browser not started');
 const tabs=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();
 ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((res,rej)=>{ws.onopen=res;ws.onerror=rej;});
 let seq=0;const pending=new Map(),listeners=new Map(),errors=[],requests=[];
 ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.id){const p=pending.get(d.id);pending.delete(d.id);d.error?p.reject(Error(JSON.stringify(d.error))):p.resolve(d.result);}else{if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails);if(d.method==='Network.requestWillBeSent')requests.push(d.params.request.url);for(const fn of listeners.get(d.method)||[])fn(d.params);}};
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
 const event=method=>new Promise(resolve=>{const fn=x=>{listeners.set(method,(listeners.get(method)||[]).filter(f=>f!==fn));resolve(x);};listeners.set(method,[...(listeners.get(method)||[]),fn]);});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true,userGesture:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const assert=(x,msg)=>{if(!x)throw Error(msg);console.log('pass: '+msg);};
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
 await send('Page.addScriptToEvaluateOnNewDocument',{source:`globalThis.storageAttempts=[]; for (const k of ['setItem','removeItem','clear']) { const original=Storage.prototype[k]; Storage.prototype[k]=function(...args){storageAttempts.push(k);return original.apply(this,args);}; }`});
 const size=async(w,h=1000,d=1)=>send('Emulation.setDeviceMetricsOverride',{width:w,height:h,deviceScaleFactor:d,mobile:false});


 await size(1440,1100);
 let ready=event('Page.loadEventFired');await send('Page.navigate',{url:new URL('./compare.html',import.meta.url).href});await ready;
 await ev(`globalThis.upload=async(slot,text)=>{const dt=new DataTransfer();dt.items.add(new File([text],slot+'.jsonl'));document.getElementById(slot+'-file').files=dt.files;await document.getElementById(slot+'-file').onchange();}`);
 const eventRow=(seq,turn,type='turn.begin',payload={})=>({run_id:'same',seq,turn,type,payload,agent_id:'a',ts:'2026-11-07T00:00:00Z'});
 const a=[eventRow(0,0,'run.config',{seed:1}),eventRow(1,1,'observation.recorded',{text:'<img src=x onerror=alert(1)>'}),eventRow(2,1,'message.sent',{message_id:'same',from:'a',to:'b',body:{type:'report',content:'<img src=x onerror=alert(1)>'}}),eventRow(3,3,'run.end')];
 const b=[eventRow(0,0,'run.config',{seed:2}),eventRow(1,2),eventRow(2,3,'run.end')];
 await ev(`upload('left',${JSON.stringify(a.map(JSON.stringify).join('\n').replace(/\\n/g,'\n'))})`);
 assert(await ev(`document.getElementById('metrics').textContent.includes('unavailable')`),'one side has no deltas');
 await ev(`upload('right',${JSON.stringify(b.map(JSON.stringify).join('\n').replace(/\\n/g,'\n'))})`);
 assert(await ev(`document.getElementById('config').textContent.includes('different logged values')`),'config mismatch visible');
 await ev(`document.getElementById('pair-turn').value='1';document.getElementById('pair-turn').onchange()`);
 assert(await ev(`document.getElementById('right-state').textContent.includes('no records') && document.getElementById('metrics').textContent.includes('unavailable')`),'missing turn unavailable');
 await ev(`document.querySelector('#left-records button').click()`);
 assert(await ev(`document.getElementById('left-detail').textContent.includes('<img') && document.querySelectorAll('img').length===0`),'imported markup is literal');
 await ev(`document.getElementById('pair-turn').value='0';document.getElementById('pair-turn').onchange()`);
 assert(await ev(`!document.getElementById('left-detail').textContent.includes('<img')`),'rewind resets future detail');
 await ev(`upload('right','{}')`);
 assert(await ev(`document.getElementById('right-error').textContent.includes('previous pair') && document.getElementById('pair-turn').value==='0'`),'failed replacement retains pair');
 await ev(`upload('right',${JSON.stringify([eventRow(0,2),eventRow(1,1)].map(JSON.stringify).join('\n').replace(/\\n/g,'\n'))})`);
 assert(await ev(`document.getElementById('right-error').textContent.includes('nondecreasing')`),'descending turns refused');
 await ev(`document.getElementById('pair-turn').focus()`);await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowDown',code:'ArrowDown'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowDown',code:'ArrowDown'});
 assert(await ev(`document.getElementById('pair-turn').value==='1'`),'keyboard turn selection');
 await fs.writeFile('/tmp/pair-desktop.png',Buffer.from((await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
 for(const [w,d,name] of [[320,1,'narrow'],[720,2,'zoom-equivalent']]){await size(w,1000,d);assert(await ev(`document.documentElement.scrollWidth<=innerWidth`),'reflow '+name);await fs.writeFile('/tmp/pair-'+name+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));}
 await ev(`document.getElementById('reset').click()`);
 assert(await ev(`document.getElementById('pair-turn').disabled && !document.getElementById('left-detail').textContent.includes('same')`),'reset clears pair');
 // Race: a slow earlier file must not overwrite a newer selection or reset.
 await ev(`globalThis.oldRead=File.prototype.arrayBuffer;globalThis.releaseRead=null;File.prototype.arrayBuffer=function(){return new Promise(resolve=>{releaseRead=()=>oldRead.call(this).then(resolve);});};globalThis.pendingLoad=upload('left',${JSON.stringify(a.map(JSON.stringify).join('\n').replace(/\\n/g,'\n'))});void 0;`);
 await ev(`File.prototype.arrayBuffer=oldRead;document.getElementById('reset').click();releaseRead();pendingLoad`);
 assert(await ev(`document.getElementById('pair-turn').disabled`),'late read cannot undo reset');
 await ev(`upload('left',${JSON.stringify(a.map(JSON.stringify).join('\n').replace(/\\n/g,'\n'))})`);
 await ev(`upload('right',${JSON.stringify(a.map(JSON.stringify).join('\n').replace(/\\n/g,'\n'))})`);
 await ev(`document.getElementById('pair-turn').value='1';document.getElementById('pair-turn').onchange();document.querySelector('[aria-label="right sent: 1 records"]').click()`);
 assert(await ev(`document.getElementById('right-detail').textContent.startsWith('right / same')`),'colliding ids remain slot-scoped');
 await ev(`upload('left','{}')`);
 assert(await ev(`document.getElementById('pair-turn').value==='1' && document.getElementById('left-error').textContent.includes('previous pair')`),'left failure retains selected turn');
 await ev(`globalThis.pendingLoad=(File.prototype.arrayBuffer=function(){return new Promise(resolve=>{releaseRead=()=>oldRead.call(this).then(resolve);});},upload('left',${JSON.stringify(a.map(JSON.stringify).join('\n').replace(/\\n/g,'\n'))}));void 0;`);
 await ev(`File.prototype.arrayBuffer=oldRead;upload('left',${JSON.stringify(b.map(JSON.stringify).join('\n').replace(/\\n/g,'\n'))})`);
 await ev(`releaseRead();pendingLoad`);
 assert(await ev(`!Array.from(document.getElementById('pair-turn').options).every(o=>o.value!=='2') && slots.left.episode.events.length===3`),'newer replacement wins over slow earlier read');
 ready=event('Page.loadEventFired');await send('Page.reload');await ready;
 assert(await ev(`document.getElementById('pair-turn').disabled && slots.left===null && slots.right===null`),'reload clears both slots');
 assert(await ev(`storageAttempts.length===0`),'no storage writes');
 assert(requests.every(url=>url.startsWith('file:')||url==='about:blank'),'no remote requests');
 assert(errors.length===0,'no browser exceptions');
}finally{ws?.close();chrome.kill();}
