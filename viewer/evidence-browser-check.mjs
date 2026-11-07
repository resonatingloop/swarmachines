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



 const downloads=await fs.mkdtemp('/tmp/swarm-evidence-downloads-');
 await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:downloads});
 await size(1440,1100);let ready=event('Page.loadEventFired');await send('Page.navigate',{url:new URL('./compare.html',import.meta.url).href});await ready;
 await ev(`globalThis.upload=async(slot,text)=>{const dt=new DataTransfer();dt.items.add(new File([text],slot+'.jsonl'));document.getElementById(slot+'-file').files=dt.files;await document.getElementById(slot+'-file').onchange();}`);
 const raw=await fs.readFile(new URL('./fixtures/freight-candidate.jsonl',import.meta.url),'utf8');
 await ev(`upload('left',${JSON.stringify(raw)})`);await ev(`upload('right',${JSON.stringify(raw)})`);
 await ev(`document.getElementById('pair-turn').value='8';document.getElementById('pair-turn').onchange();document.getElementById('export-add').click();document.getElementById('export-prepare').onclick()`);
 const json=await ev(`document.getElementById('export-json-preview').textContent`),md=await ev(`document.getElementById('export-markdown-preview').textContent`),packet=JSON.parse(json);
 assert(packet.selection.turns[0]===8 && packet.turns[0].delta.sent===0,'preview has selected-turn comparison');
 assert(packet.sources.left.sha256==='f4b6a3432a69577074d4c38a826d8160c793a5b83ba73f654a73a9aa1100dcad','browser hashes exact source bytes');
 await ev(`document.getElementById('export-json').click();document.getElementById('export-markdown').click()`);
 let savedJSON,savedMD;
 for(let i=0;i<50;i++){try{savedJSON=await fs.readFile(downloads+'/swarmachines-evidence.json','utf8');savedMD=await fs.readFile(downloads+'/swarmachines-evidence.md','utf8');break;}catch{await new Promise(r=>setTimeout(r,100));}}
 assert(savedJSON===json&&savedMD===md,'both downloaded artifacts equal exact preview');
 await ev(`document.getElementById('pair-turn').value='9';document.getElementById('pair-turn').onchange()`);
 assert(await ev(`document.getElementById('export-json-preview').textContent===${JSON.stringify(json)}`),'cursor alone preserves prepared packet');
 await ev(`upload('left','{}')`);
 assert(await ev(`!document.getElementById('export-json').disabled && document.getElementById('export-json-preview').textContent===${JSON.stringify(json)}`),'failed source replacement preserves packet');
 await ev(`document.getElementById('export-add').click()`);
 assert(await ev(`document.getElementById('export-json').disabled && !document.getElementById('export-json-preview').textContent`),'selection change invalidates packet');
 await ev(`document.getElementById('export-prepare').onclick()`);
 await ev(`upload('right',${JSON.stringify(raw)})`);
 assert(await ev(`!document.getElementById('export-selection').textContent && document.getElementById('export-json').disabled`),'successful right replacement clears selection');
 await ev(`document.getElementById('export-add').click();document.getElementById('export-prepare').onclick()`);
 await ev(`globalThis.realPrepare=Evidence.prepare;globalThis.releasePrepare=null;Evidence.prepare=(...args)=>new Promise(resolve=>{releasePrepare=()=>realPrepare(...args).then(resolve);});globalThis.delayedPrepare=document.getElementById('export-prepare').onclick();void 0;`);
 await ev(`document.getElementById('reset').click();releasePrepare();delayedPrepare`);
 assert(await ev(`document.getElementById('export-json').disabled && !document.getElementById('export-json-preview').textContent`),'late prepare cannot resurrect reset');
 await ev(`Evidence.prepare=realPrepare;globalThis.realHash=Evidence.sha256;globalThis.releaseHash=null;Evidence.sha256=(bytes)=>new Promise(resolve=>{releaseHash=()=>realHash(bytes).then(resolve);});globalThis.delayedImport=upload('left',${JSON.stringify(raw)});void 0;`);
 for(let i=0;i<30&&!await ev('!!releaseHash');i++)await new Promise(r=>setTimeout(r,50));
 assert(await ev(`document.getElementById('export-prepare').disabled`),'pending hash disables export');
 await ev(`document.getElementById('reset').click();releaseHash();delayedImport`);
 assert(await ev(`slots.left===null && document.getElementById('export-json').disabled`),'late hash cannot resurrect source');
 await ev(`Evidence.sha256=async()=>{throw Error('cryptography unavailable')};upload('left',${JSON.stringify(raw)})`);
 assert(await ev(`slots.left!==null && document.getElementById('export-status').textContent.includes('cryptography unavailable') && document.getElementById('export-prepare').disabled`),'hash failure leaves comparison usable with export disabled');
 await ev(`Evidence.sha256=realHash;upload('left',${JSON.stringify(raw)})`);await ev(`upload('right',${JSON.stringify(raw)})`);
 await ev(`document.getElementById('export-add').focus()`);await send('Input.dispatchKeyEvent',{type:'rawKeyDown',key:' ',code:'Space',windowsVirtualKeyCode:32,nativeVirtualKeyCode:32});await send('Input.dispatchKeyEvent',{type:'keyUp',key:' ',code:'Space',windowsVirtualKeyCode:32,nativeVirtualKeyCode:32});
 assert(await ev(`document.getElementById('export-selection').textContent.includes('remove turn')`),'keyboard selects turn');
 await ev(`document.getElementById('export-prepare').onclick();`);
 await ev(`document.querySelectorAll('#evidence-export details').forEach(d=>d.open=true);document.getElementById('evidence-export').scrollIntoView()`);
 await fs.writeFile(downloads+'/desktop.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 for(const [w,d] of [[320,1],[720,2]]){await size(w,1000,d);await ev(`document.getElementById('evidence-export').scrollIntoView()`);assert(await ev(`document.documentElement.scrollWidth<=innerWidth`),'export reflow '+w);}
 await size(320,1000,1);await ev(`document.getElementById('evidence-export').scrollIntoView()`);
 await fs.writeFile(downloads+'/narrow.png',Buffer.from((await send('Page.captureScreenshot',{format:'png'})).data,'base64'));
 ready=event('Page.loadEventFired');await send('Page.reload');await ready;
 assert(await ev(`document.getElementById('export-json').disabled && !document.getElementById('export-json-preview').textContent`),'reload clears packet');
 assert(await ev(`storageAttempts.length===0`),'no storage writes');
 assert(requests.every(url=>url.startsWith('file:')||url.startsWith('blob:')||url==='about:blank'),'no remote requests');
 assert(errors.length===0,'no browser exceptions');console.log('artifacts: '+downloads);
}finally{ws?.close();chrome.kill();}
