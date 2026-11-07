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
 let ready=event('Page.loadEventFired'); await send('Page.navigate',{url:new URL('./index.html',import.meta.url).href}); await ready;
 await ev(`document.getElementById('sample').click()`);
 assert(await ev(`document.getElementById('identity').textContent.includes('67 records')`),'sample opens offline');
 await ev(`go(66)`);
 assert(await ev(`document.querySelectorAll('#messages .card').length===8 && document.getElementById('world').textContent.includes('reported summary')`),'end evidence');
 await fs.writeFile('/tmp/replay-desktop.png',Buffer.from((await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
 await ev(`go(0)`);
 assert(await ev(`!document.querySelectorAll('#messages .card').length && !document.getElementById('world').textContent.includes('reported summary')`),'rewind removes future evidence');
 await ev(`document.getElementById('cursor').focus()`);
 await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowRight',code:'ArrowRight'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowRight',code:'ArrowRight'});
 assert(await ev(`document.getElementById('cursor').value==='1'`),'keyboard cursor');
 await ev(`go(65);document.getElementById('play').click()`);await new Promise(r=>setTimeout(r,800));
 assert(await ev(`cursor===66 && timer===null`),'play stops at end');
 await ev(`async function upload(text,name='test.jsonl'){const dt=new DataTransfer();dt.items.add(new File([text],name));document.getElementById('file').files=dt.files;await document.getElementById('file').onchange();} upload('{}')`);
 assert(await ev(`cursor===66 && document.getElementById('error').textContent.includes('line 1')`),'failed import retains prior cursor');
 await ev(`upload(' '.repeat(5*1024*1024+1))`);
 assert(await ev(`cursor===66 && document.getElementById('error').textContent.includes('5 mib')`),'oversized file rejected before read');
 await ev(`upload(new Uint8Array([255]))`);
 assert(await ev(`cursor===66 && document.getElementById('error').textContent.includes('could not load')`),'invalid utf-8 rejected');
 await ev(`upload(JSON.stringify({...episode.events[0], type:'future.record',payload:{value:'<img src=https://example.invalid onerror=alert(1)>'}}))`);
 assert(await ev(`document.getElementById('detail').textContent.includes('<img') && document.querySelectorAll('img').length===0 && document.getElementById('warnings').textContent.includes('unsupported')`),'unknown markup remains inert');
 await ev(`document.getElementById('sample').click();go(66)`);
 for(const [w,d,name] of [[320,1,'narrow'],[720,2,'zoom-equivalent']]){
  await size(w,1000,d);
  assert(await ev(`document.documentElement.scrollWidth<=innerWidth`),'no horizontal overflow '+name);
  await fs.writeFile('/tmp/replay-'+name+'.png',Buffer.from((await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})).data,'base64'));
 }
 await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 assert(await ev(`matchMedia('(prefers-reduced-motion: reduce)').matches`),'reduced motion');
 assert(await ev(`storageAttempts.length===0`),'no storage writes');
 ready=event('Page.loadEventFired');await send('Page.reload');await ready;
 assert(await ev(`document.getElementById('identity').textContent.includes('no episode loaded')`),'reload clears imported data');
 assert(requests.every(url=>url.startsWith('file:') || url==='about:blank'),'no remote requests');
 assert(errors.length===0,'no browser exceptions');
}finally{ws?.close();chrome.kill();}
