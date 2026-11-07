'use strict';
const ExportUI=(()=>{
  const chosen=new Set(),loading={left:false,right:false},urls=new Set();
  let prepared=null,generation=0,preparing=false;
  const busy=()=>loading.left||loading.right;
  const ready=()=>slots.left?.sha256&&slots.right?.sha256;
  function revoke(){for(const url of urls)URL.revokeObjectURL(url);urls.clear();}
  function invalidate(){generation++;preparing=false;prepared=null;revoke();el('export-json-preview').textContent='';el('export-markdown-preview').textContent='';el('export-error').textContent='';}
  function refresh(){
    el('export-add').disabled=selectedTurn===null||busy()||chosen.size>=32||chosen.has(selectedTurn);
    el('export-clear').disabled=!chosen.size||busy();
    el('export-prepare').disabled=busy()||preparing||!ready()||!chosen.size;
    el('export-json').disabled=el('export-markdown').disabled=busy()||preparing||!prepared;
    el('export-selection').replaceChildren();
    for(const turn of [...chosen].sort((a,b)=>a-b)){const b=make('button',`remove turn ${turn}`);b.disabled=busy();b.onclick=()=>{chosen.delete(turn);invalidate();refresh();};el('export-selection').append(b);}
    const errors=['left','right'].filter(s=>slots[s]?.hashError).map(s=>`${s}: ${slots[s].hashError}`);
    el('export-status').textContent=busy()?'source import/hash in progress; export paused.':preparing?'preparing evidence…':errors.length?errors.join(' · '):prepared?`prepared ${chosen.size} turns / json ${prepared.sizes.json} bytes / markdown ${prepared.sizes.markdown} bytes / packet ${prepared.packet.packet_id}`:!ready()?'load and hash both sources to export.':`${chosen.size} / 32 turns selected; prepare to inspect the exact contents.`;
  }
  function sourceAccepted(){chosen.clear();invalidate();refresh();}
  function pending(slot,value){loading[slot]=value;if(value){generation++;preparing=false;}refresh();}
  function reset(){loading.left=loading.right=false;sourceAccepted();}
  el('export-add').onclick=()=>{if(selectedTurn===null||busy()||chosen.size>=32)return;chosen.add(selectedTurn);invalidate();refresh();};
  el('export-clear').onclick=()=>{chosen.clear();invalidate();refresh();};
  el('export-prepare').onclick=async()=>{
    if(busy()||!ready()||!chosen.size)return;
    const version=++generation;preparing=true;el('export-error').textContent='';refresh();
    try{
      const result=await Evidence.prepare({left:slots.left,right:slots.right},[...chosen]);
      if(version!==generation)return;
      prepared=result;el('export-json-preview').textContent=result.json;el('export-markdown-preview').textContent=result.markdown;
    }catch(error){if(version===generation){prepared=null;el('export-json-preview').textContent='';el('export-markdown-preview').textContent='';el('export-error').textContent=error.message;}}
    finally{if(version===generation){preparing=false;refresh();}}
  };
  function download(kind){
    if(!prepared||busy()||preparing)return;
    const isJSON=kind==='json',url=URL.createObjectURL(new Blob([prepared[kind]],{type:isJSON?'application/json;charset=utf-8':'text/markdown;charset=utf-8'}));urls.add(url);
    const a=document.createElement('a');a.href=url;a.download=isJSON?'swarmachines-evidence.json':'swarmachines-evidence.md';document.body.append(a);a.click();a.remove();
    setTimeout(()=>{URL.revokeObjectURL(url);urls.delete(url);},1000);
  }
  el('export-json').onclick=()=>download('json');el('export-markdown').onclick=()=>download('markdown');
  window.addEventListener('pagehide',revoke);refresh();return {refresh,pending,sourceAccepted,reset};
})();
globalThis.ExportUI=ExportUI;
