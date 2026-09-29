import {useState} from 'react';
import {post,useGet} from './api';

export default function JevAssistant({onSearch,endpoint='/jev/describe',placeholder='A white Creta with a black roof, a red door panel and a roof rack',title='Describe a vehicle in your own words',open=false}:{onSearch:(filters:any)=>Promise<void>|void;endpoint?:string;placeholder?:string;title?:string;open?:boolean}){
 const [text,setText]=useState(''),[result,setResult]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const status=useGet<any>('/jev/status');
 const interpret=async()=>{setBusy(true);setError('');setResult(null);try{const response=await post(endpoint,{text});await onSearch(response.filters);setResult(response)}catch(e){setError((e as Error).message)}finally{setBusy(false);status.refetch()}};
 return <details className="panel jev-assistant" open={open}><summary>{title} <span className="muted">Jev · optional</span></summary>
 <p className="muted">Only the text you enter is sent to Jev through Vercel when you click below. Camera evidence stays local.</p>
 <label>Vehicle description<textarea aria-label="Jev vehicle description" maxLength={600} disabled={busy} value={text} onChange={e=>{setText(e.target.value);setResult(null)}} placeholder={placeholder}/></label>
 <div className="search-footer"><button className="primary" type="button" disabled={busy||text.trim().length<5||status.data?.configured===false} onClick={interpret}>{busy?'Searching…':'Search with Jev'}</button><span className="muted">{status.data?`${status.data.requests}/${status.data.max_requests} online requests used · repeated text is cached`:'Checking availability…'}</span></div>
 {status.data?.configured===false&&<p className="muted">Jev is not connected. Use the search filters below.</p>}
 {error&&<p role="alert" className="conflict-text">{error}</p>}
 {result&&<div className="jev-result" role="status"><p>{result.cached?'Search complete using saved Jev filters':'Search complete using Jev filters'} · results below</p>
  {result.summary?(result.summary.length?<ul className="jev-summary">{result.summary.map((s:string)=><li key={s}>{s}</li>)}</ul>:<p className="muted">Jev found no supported details in this description. All filters were cleared.</p>)
  :<dl>{Object.entries(result.filters).filter(([,v])=>Array.isArray(v)?v.length:!!v).map(([k,v])=><div key={k}><dt>{k.replaceAll('_',' ')}</dt><dd>{Array.isArray(v)?v.join(', '):typeof v==='object'?Object.entries(v as any).map(([a,b])=>a+': '+b).join(', '):String(v)}</dd></div>)}</dl>}
  <p className="muted">Filters have been applied automatically. You can edit them below. Unstated details remain unknown; Jev does not verify identity.</p></div>}
 </details>
}
