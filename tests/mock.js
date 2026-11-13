(()=>{
  const store=JSON.parse(sessionStorage.getItem('MOCK_CLOUD_SEED')||'{}');
  window.__store=store; window.__aiCalls=[]; window.__aiFail=null;
  const snap=(id,v)=>({id,exists:v!==undefined,data:()=>v===undefined?undefined:JSON.parse(JSON.stringify(v)),metadata:{fromCache:false,hasPendingWrites:false}});
  const db={collection(p){ return {doc(k){ const path=p+'/'+k; return {
    get:async()=>snap(k,store[path]), set:async(d)=>{ store[path]=JSON.parse(JSON.stringify(d)); }, delete:async()=>{ delete store[path]; } }; } }; }};
  const sample=async(input,opts)=>{ window.__aiCalls.push(input); if(window.__aiFail) throw window.__aiFail; const t=window.__aiText||"今天辛苦了。先從最小的一件開始就好。";
    if(opts&&opts.onText) opts.onText({text:t,delta:t}); return {text:t,truncated:false}; };
  sample.json=async(input)=>{ window.__aiCalls.push(input); if(window.__aiFail) throw window.__aiFail; return window.__aiJson ? window.__aiJson(input) : {}; };
  window.__saved=[];
  const downloads={save:async(r)=>{ const size=r.data instanceof Blob?r.data.size:String(r.data).length; window.__saved.push({filename:r.filename,size}); return {status:"saved"}; }};
  window.claude={use:async n=> n==="sample"?sample : n==="db"?db : n==="user"?{id:async()=>"user1"} : n==="downloads"?downloads : null};
})();
